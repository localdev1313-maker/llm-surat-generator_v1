package com.pussiber.suratgenerator.ui.common

import android.app.Activity
import android.content.Intent
import android.speech.RecognizerIntent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember

/**
 * Pengendali Speech-to-Text bersama — menggantikan duplikasi launcher + intent
 * yang sebelumnya disalin di 3 layar dengan sedikit perbedaan prompt.
 *
 * Pemakaian di layar:
 * ```
 * val stt = rememberSttController(onUnsupported = { Toast...show() })
 * OutlinedTextField(
 *     ...
 *     trailingIcon = {
 *         IconButton(onClick = { stt.launch { spoken -> field = ... } }) { Icon(Mic) }
 *     }
 * )
 * ```
 */
class SttController internal constructor() {
    internal var intentLauncher: ((Intent) -> Unit)? = null
    private var target: ((String) -> Unit)? = null

    /** Minta pengguna berbicara; hasil dikirim ke [onResult] (satu kata/frasa). */
    fun launch(onResult: (String) -> Unit) {
        target = onResult
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "id-ID")
            putExtra(RecognizerIntent.EXTRA_PROMPT, "Diktekan materi naskah...")
        }
        intentLauncher?.invoke(intent)
    }

    /** Terima hasil dari activity result — dipanggil internal oleh helper. */
    internal fun deliver(spoken: String) {
        target?.invoke(spoken)
        target = null
    }
}

@Composable
fun rememberSttController(onUnsupported: () -> Unit): SttController {
    val controller = remember { SttController() }
    val launcher: ActivityResultLauncher<Intent> = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK && result.data != null) {
            val matches = result.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
            if (!matches.isNullOrEmpty()) controller.deliver(matches[0])
        }
    }
    LaunchedEffect(controller) {
        controller.intentLauncher = { intent ->
            try {
                launcher.launch(intent)
            } catch (e: Exception) {
                onUnsupported()
            }
        }
    }
    return controller
}
