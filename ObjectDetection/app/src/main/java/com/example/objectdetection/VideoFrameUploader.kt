package com.example.objectdetection.network

import android.graphics.Bitmap
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody
import java.io.ByteArrayOutputStream

object VideoFrameUploader {

    suspend fun uploadFrame(bitmap: Bitmap) {
        try {
            val byteArray = bitmapToByteArray(bitmap)
            val requestFile = RequestBody.create("image/jpeg".toMediaTypeOrNull(), byteArray)
            val body = MultipartBody.Part.createFormData("file", "frame.jpg", requestFile)

            val response = withContext(Dispatchers.IO) {
                RetrofitClient.apiService.uploadFrame(body)
            }

            if (response.isSuccessful) {
                Log.d("Frame Upload", "Frame uploaded successfully")
            } else {
                Log.e("Frame Upload", "Upload failed: ${response.errorBody()?.string()}")
            }
        } catch (e: Exception) {
            Log.e("Frame Upload", "Exception: ${e.message}", e)
        }
    }

    private fun bitmapToByteArray(bitmap: Bitmap): ByteArray {
        val stream = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.JPEG, 90, stream) // Compress to JPEG
        return stream.toByteArray()
    }
}
