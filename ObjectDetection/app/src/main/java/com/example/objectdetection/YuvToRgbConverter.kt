package com.example.objectdetection

import android.content.Context
import android.graphics.Bitmap
import android.graphics.ImageFormat
import android.media.Image
import androidx.camera.core.ImageProxy
import android.renderscript.*

class YuvToRgbConverter(context: Context) {
    private val rs: RenderScript = RenderScript.create(context)
    private val script: ScriptIntrinsicYuvToRGB = ScriptIntrinsicYuvToRGB.create(rs, Element.U8_4(rs))

    fun yuvToRgb(image: ImageProxy, output: Bitmap) {
        val yuvBytes = imageToByteArray(image.image!!)
        val yuvType = Type.Builder(rs, Element.U8(rs)).setX(yuvBytes.size).create()
        val input = Allocation.createTyped(rs, yuvType, Allocation.USAGE_SCRIPT)
        val outputAlloc = Allocation.createFromBitmap(rs, output)

        input.copyFrom(yuvBytes)
        script.setInput(input)
        script.forEach(outputAlloc)
        outputAlloc.copyTo(output)

        input.destroy()
        outputAlloc.destroy()
    }

    private fun imageToByteArray(image: Image): ByteArray {
        val yBuffer = image.planes[0].buffer
        val uBuffer = image.planes[1].buffer
        val vBuffer = image.planes[2].buffer

        val ySize = yBuffer.remaining()
        val uSize = uBuffer.remaining()
        val vSize = vBuffer.remaining()

        val nv21 = ByteArray(ySize + uSize + vSize)
        yBuffer.get(nv21, 0, ySize)
        vBuffer.get(nv21, ySize, vSize)
        uBuffer.get(nv21, ySize + vSize, uSize)

        return nv21
    }
}
