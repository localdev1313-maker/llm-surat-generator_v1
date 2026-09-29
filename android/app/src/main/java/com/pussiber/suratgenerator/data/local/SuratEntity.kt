package com.pussiber.suratgenerator.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "surat_table")
data class SuratEntity(
    @PrimaryKey val id: String,
    val jenisSurat: String, // "nota_dinas" or "surat_umum"
    val perihal: String,
    val kepada: String,
    val dari: String,
    val tanggalBuat: Long = System.currentTimeMillis(),
    val isDraft: Boolean = false,
    val localFilePath: String? = null,
    val downloadUrl: String? = null,
    val jsonContent: String
)
