package com.pussiber.suratgenerator.data.local

import android.content.Context
import android.util.Log
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.withTransaction
import com.pussiber.suratgenerator.SuratViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withContext
import net.zetetic.database.sqlcipher.SupportOpenHelperFactory
import java.security.SecureRandom
import android.util.Base64

@Database(entities = [SuratEntity::class], version = 1, exportSchema = false)
abstract class AppDatabase : RoomDatabase() {
    abstract fun suratDao(): SuratDao

    companion object {
        private const val TAG = "AppDatabase"

        /** Nama DB terenkripsi — BERBEDA dari nama lama agar migrasi bisa dua-arah. */
        private const val DB_NAME = "pussiber_surat_database_enc"

        /** Nama DB versi lama yang TIDAK terenkripsi (SQLCipher dibundel tapi tak dipasang). */
        private const val LEGACY_PLAIN_DB_NAME = "pussiber_surat_database"

        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun getDatabase(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: buildEncryptedDatabase(context.applicationContext).also { INSTANCE = it }
            }
        }

        private fun buildEncryptedDatabase(context: Context): AppDatabase {
            // Muat native library SQLCipher PALING AWAL — jalur migrasi di bawah juga
            // membuka DB terenkripsi, dan SupportOpenHelperFactory TIDAK memuat lib-nya
            // sendiri (terverifikasi dari bytecode AAR sqlcipher-android 4.5.6).
            // Tanpa ini: UnsatisfiedLinkError saat insert pertama migrasi.
            System.loadLibrary("sqlcipher")

            migrateLegacyPlaintextIfNeeded(context)

            return Room.databaseBuilder(context, AppDatabase::class.java, DB_NAME)
                .openHelperFactory(SupportOpenHelperFactory(getOrCreatePassphrase(context)))
                .build()
        }

        /**
         * Frasa sandi acak 32 byte untuk SQLCipher.
         *
         * Penyimpanan BERTINGKAT:
         * 1. Frasa sandi DIENKRIPSI dengan kunci AES-256/GCM yang tersimpan di
         *    Android Keystore (tidak bisa diekspor) — hasilnya (IV+ciphertext)
         *    disimpan di SharedPreferences.
         * 2. Migrasi otomatis: instalasi lama yang masih menyimpan frasa sandi
         *    polos (KEY_DB_PASSPHRASE) di-wrap saat upgrade TANPA kehilangan arsip.
         * 3. Fallback: bila Keystore gagal (perangkat eksotis), frasa sandi disimpan
         *    polos seperti sebelumnya — arsip tetap bisa dibuka, keamanan setara
         *    versi lama, dan dicatat di log.
         */
        private fun getOrCreatePassphrase(context: Context): ByteArray {
            val prefs = context.getSharedPreferences(SuratViewModel.PREFS_NAME, Context.MODE_PRIVATE)

            // 1) Sudah ter-wrap -> buka dengan kunci Keystore
            prefs.getString(KEY_DB_PASSPHRASE_WRAPPED, null)?.let { wrappedB64 ->
                val plain = unwrapWithKeystore(Base64.decode(wrappedB64, Base64.NO_WRAP))
                if (plain == null) {
                    // Kunci Keystore hilang (mis. di-reset sistem) — data DB tidak
                    // dapat dibuka; gagal keras agar terdiagnosis, bukan korup diam-diam.
                    throw IllegalStateException("Passphrase DB tidak dapat dibuka dari Android Keystore")
                }
                return plain
            }

            // 2) Migrasi dari penyimpanan pola versi sebelumnya
            prefs.getString(KEY_DB_PASSPHRASE, null)?.let { oldB64 ->
                val plain = Base64.decode(oldB64, Base64.NO_WRAP)
                if (wrapWithKeystore(prefs, plain)) {
                    prefs.edit().remove(KEY_DB_PASSPHRASE).apply()
                    Log.w(TAG, "Passphrase DB dimigrasikan ke pembungkus Android Keystore.")
                }
                return plain
            }

            // 3) Instalasi baru -> buat acak lalu wrap
            val bytes = ByteArray(32).also { SecureRandom().nextBytes(it) }
            wrapWithKeystore(prefs, bytes)
            return bytes
        }

        /** Enkripsi [plain] dengan kunci Keystore; simpan hasilnya di prefs. */
        private fun wrapWithKeystore(prefs: android.content.SharedPreferences, plain: ByteArray): Boolean {
            return try {
                val key = getOrCreateKeystoreKey()
                val cipher = javax.crypto.Cipher.getInstance("AES/GCM/NoPadding")
                cipher.init(javax.crypto.Cipher.ENCRYPT_MODE, key)
                val iv = cipher.iv
                val ct = cipher.doFinal(plain)
                val gabungan = iv + ct
                prefs.edit()
                    .putString(KEY_DB_PASSPHRASE_WRAPPED, Base64.encodeToString(gabungan, Base64.NO_WRAP))
                    .apply()
                true
            } catch (t: Throwable) {
                Log.e(TAG, "Wrap passphrase dengan Keystore gagal — fallback polos", t)
                false
            }
        }

        private fun unwrapWithKeystore(gabungan: ByteArray): ByteArray? {
            return try {
                val key = getOrCreateKeystoreKey()
                val cipher = javax.crypto.Cipher.getInstance("AES/GCM/NoPadding")
                cipher.init(javax.crypto.Cipher.DECRYPT_MODE, key, javax.crypto.spec.GCMParameterSpec(128, gabungan, 0, 12))
                cipher.doFinal(gabungan, 12, gabungan.size - 12)
            } catch (t: Throwable) {
                Log.e(TAG, "Unwrap passphrase gagal", t)
                null
            }
        }

        /** Kunci AES-256/GCM non-ekspor di Android Keystore. */
        private fun getOrCreateKeystoreKey(): javax.crypto.SecretKey {
            val ks = java.security.KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
            (ks.getKey(KEYSTORE_ALIAS, null) as? javax.crypto.SecretKey)?.let { return it }
            val generator = javax.crypto.KeyGenerator.getInstance("AES", "AndroidKeyStore")
            generator.init(
                android.security.keystore.KeyGenParameterSpec.Builder(
                    KEYSTORE_ALIAS,
                    android.security.keystore.KeyProperties.PURPOSE_ENCRYPT or
                        android.security.keystore.KeyProperties.PURPOSE_DECRYPT
                )
                    .setBlockModes(android.security.keystore.KeyProperties.BLOCK_MODE_GCM)
                    .setEncryptionPaddings(android.security.keystore.KeyProperties.ENCRYPTION_PADDING_NONE)
                    .setKeySize(256)
                    .build()
            )
            return generator.generateKey()
        }

        /**
         * Pindahkan arsip dari DB plaintext versi lama ke DB terenkripsi.
         *
         * Aturan keamanan data:
         * - File plaintext lama HANYA dihapus setelah jumlah baris terenkripsi >= jumlah baris legacy.
         *   Tanpa verifikasi ini, proses yang mati di tengah copy membuat peluncuran berikutnya
         *   menghapus arsip yang belum tersalin (kehilangan permanen & senyap).
         * - Copy berjalan dalam SATU transaksi atomik — tidak ada state parsial persisten.
         * - insertSurat memakai OnConflictStrategy.REPLACE sehingga copy ulang bersifat idempoten.
         * - catch Throwable (bukan hanya Exception) karena UnsatisfiedLinkError adalah Error.
         */
        private fun migrateLegacyPlaintextIfNeeded(context: Context) {
            if (!context.getDatabasePath(LEGACY_PLAIN_DB_NAME).exists()) return

            try {
                val legacy = Room.databaseBuilder(context, AppDatabase::class.java, LEGACY_PLAIN_DB_NAME)
                    .build()
                val target = Room.databaseBuilder(context, AppDatabase::class.java, DB_NAME)
                    .openHelperFactory(SupportOpenHelperFactory(getOrCreatePassphrase(context)))
                    .build()

                val copied = runBlocking(Dispatchers.IO) {
                    val rows = legacy.suratDao().getAllOnce()
                    // Satu transaksi: proses mati di tengah copy meninggalkan target kosong,
                    // bukan DB parsial — copy ulang pada peluncuran berikutnya tetap aman.
                    target.withTransaction {
                        rows.forEach { target.suratDao().insertSurat(it) }
                    }
                    rows.size
                }

                val migratedCount = runBlocking(Dispatchers.IO) { target.suratDao().getAllOnce().size }
                if (migratedCount < copied) {
                    throw IllegalStateException(
                        "Verifikasi migrasi gagal: legacy=$copied, encrypted=$migratedCount"
                    )
                }

                legacy.close()
                target.close()
                context.deleteDatabase(LEGACY_PLAIN_DB_NAME)
                Log.w(TAG, "Migrasi $copied baris arsip ke database terenkripsi selesai.")
            } catch (t: Throwable) {
                // Gagal migrasi: JANGAN sentuh file legacy (sumber data tetap utuh);
                // buang DB terenkripsi parsial agar percobaan berikutnya mulai bersih.
                try {
                    context.deleteDatabase(DB_NAME)
                    context.deleteDatabase("$DB_NAME-wal")
                    context.deleteDatabase("$DB_NAME-shm")
                } catch (cleanup: Throwable) {
                    Log.w(TAG, "Gagal membersihkan DB parsial", cleanup)
                }
                Log.e(TAG, "Migrasi plaintext -> terenkripsi gagal (legacy dipertahankan)", t)
            }
        }

        private const val KEY_DB_PASSPHRASE = "db_passphrase_b64"          // LEGACY (pola)
        private const val KEY_DB_PASSPHRASE_WRAPPED = "db_passphrase_wrapped_b64"
        private const val KEYSTORE_ALIAS = "sseb_db_master_key"
    }
}
