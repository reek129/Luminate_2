package com.example.objectdetection.network

import okhttp3.MultipartBody
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part

interface ApiService {
    @Multipart
    @POST("upload-frame") // Adjusted to match Retrofit base URL structure
    suspend fun uploadFrame(
        @Part frame: MultipartBody.Part
    ): Response<ResponseBody>

    @POST("get-audio") // Adjusted endpoint formatting for consistency
    suspend fun getAudio(): Response<ResponseBody> // Receives audio response
}
