package com.example.objectdetection

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.Box
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.example.objectdetection.network.VideoFrameUploader
import com.example.objectdetection.ui.theme.ObjectDetectionTheme
import java.nio.ByteBuffer
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.Dispatchers


class MainActivity : ComponentActivity() {
    private lateinit var cameraExecutor: ExecutorService
    private var previewView: PreviewView? = null
    private lateinit var yuvToRgbConverter: YuvToRgbConverter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Initialize camera executor
        cameraExecutor = Executors.newSingleThreadExecutor()
        yuvToRgbConverter = YuvToRgbConverter(this)


        setContent {
            ObjectDetectionTheme {
                Box(modifier = Modifier.fillMaxSize()) {
                    AndroidView(
                        factory = { context ->
                            PreviewView(context).apply {
                                scaleType = PreviewView.ScaleType.FILL_CENTER
                                previewView = this
                            }
                        },
                        modifier = Modifier.fillMaxSize()
                    )
                }
            }

            // Request permission when the UI is created
            LaunchedEffect(Unit) {
                requestCameraPermission()
            }
        }
    }

    private fun requestCameraPermission() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            Log.d("CameraX", "Permission granted, starting camera...")
            startCamera()
        } else {
            Log.d("CameraX", "Requesting camera permission...")
            requestPermissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        if (isGranted) {
            Log.d("CameraX", "Permission granted, starting camera...")
            startCamera()
        } else {
            Log.e("CameraX", "Permission denied, closing app")
            Toast.makeText(this, "Camera permission is required", Toast.LENGTH_SHORT).show()
            finish() // Close the app if permission is denied
        }
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)

        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()
            val preview = Preview.Builder().build().also {
                previewView?.surfaceProvider?.let { provider -> it.setSurfaceProvider(provider) }
            }

            val imageAnalyzer = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_YUV_420_888)
                .build()

            imageAnalyzer.setAnalyzer(cameraExecutor) { image ->
                processVideoFrame(image)
            }

            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA

            try {
                cameraProvider.unbindAll()
                val camera = cameraProvider.bindToLifecycle(this, cameraSelector, preview, imageAnalyzer)
                Log.d("CameraX", "Camera started successfully: $camera")
            } catch (exc: Exception) {
                Log.e("CameraX", "Camera failed to start", exc)
            }
        }, ContextCompat.getMainExecutor(this))
    }

    private var lastTimestamp = 0L

    private fun processVideoFrame(image: ImageProxy) {
        val currentTime = System.currentTimeMillis()

        // Allow only 1 frame per second
        if (currentTime - lastTimestamp < 500) {
            image.close() // Skip frame if 1 second has not passed
            return
        }

        lastTimestamp = currentTime

        try {
            val bitmap = Bitmap.createBitmap(image.width, image.height, Bitmap.Config.ARGB_8888)
            yuvToRgbConverter.yuvToRgb(image, bitmap) // Convert YUV to RGB

            Log.d("Frame Capture", "Captured frame, sending to server...")

            // ✅ Launch coroutine for suspend function
            lifecycleScope.launch(Dispatchers.IO) { // Move network call to IO thread
                VideoFrameUploader.uploadFrame(bitmap)
            }


        } catch (e: Exception) {
            Log.e("Frame Capture", "Error processing frame: ${e.message}", e)
        } finally {
            image.close() // Always close image to prevent memory leak
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
    }
}
