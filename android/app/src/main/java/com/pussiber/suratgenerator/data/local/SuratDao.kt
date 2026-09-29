package com.pussiber.suratgenerator.data.local

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface SuratDao {
    @Query("SELECT * FROM surat_table ORDER BY tanggalBuat DESC")
    fun getAllSurat(): Flow<List<SuratEntity>>

    @Query("SELECT * FROM surat_table WHERE isDraft = 1 ORDER BY tanggalBuat DESC")
    fun getDrafts(): Flow<List<SuratEntity>>

    @Query("SELECT * FROM surat_table WHERE isDraft = 0 ORDER BY tanggalBuat DESC")
    fun getArchivedSurat(): Flow<List<SuratEntity>>

    /** Akses satu-kali seluruh baris — dipakai migrasi DB plaintext → SQLCipher. */
    @Query("SELECT * FROM surat_table")
    suspend fun getAllOnce(): List<SuratEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertSurat(surat: SuratEntity)

    @Delete
    suspend fun deleteSurat(surat: SuratEntity)
}
