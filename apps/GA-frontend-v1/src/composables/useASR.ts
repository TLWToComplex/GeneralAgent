import { ref, shallowRef, onUnmounted } from 'vue';
import EventBus, { AUDIO_EVENTS } from '@/utils/EventBus';

interface ASROptions {
  serverAddress: string;
  onError?: (msg: string | Error) => void;
  onSuccess?: (msg: string) => void;
  publicPath?: string;
}

interface SpeechRecognitionState {
  pendingOnlineText: string;
  lastRecognizedText: string;
}

// Declare global types for external libraries
declare global {
  interface Window {
    Recorder: any;
    WSConnecter: any;
  }
}

/**
 * ASR (Automatic Speech Recognition) Composable
 * Encapsulates logic for recording audio and sending it to a WebSocket server for recognition.
 */
export function useASR(options: ASROptions) {
  const {
    serverAddress,
    onError = (msg: string | Error) => console.error(msg),
    onSuccess = (_msg: string) => {},
    publicPath = ''
  } = options;

  const recorder = shallowRef<any>(null);
  const wsConnecter = shallowRef<any>(null);
  const sampleBuf = ref(new Int16Array());
  const audioLevel = ref(0);
  const audioFrequency = ref(0); // 0-1 representing rough frequency/pitch
  const isVoiceActive = ref(false);
  const isConnecting = ref(false);
  const connectionFailed = ref(false);
  
  const speechRecognitionState = ref<SpeechRecognitionState>({
    pendingOnlineText: '',
    lastRecognizedText: ''
  });

  // 监听停止ASR事件
  const stopAsrHandler = () => {
    if (isVoiceActive.value) {
      stopRecording();
    }
  };
  EventBus.on(AUDIO_EVENTS.STOP_ASR, stopAsrHandler);

  const loadScript = (src: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      const fullSrc = `${publicPath}${src}`;
      // Check if already loaded
      const existingScripts = document.querySelectorAll('script');
      const isLoaded = Array.from(existingScripts).some(s => s.src.includes(src.split('/').pop() || ''));
      
      if (isLoaded) {
        resolve();
        return;
      }

      const script = document.createElement('script');
      script.src = fullSrc;
      script.async = false;
      script.onload = () => resolve();
      script.onerror = () => reject(`Failed to load script: ${fullSrc}`);
      document.head.appendChild(script);
    });
  };

  const initRecorder = async () => {
    try {
      // Load required scripts sequentially or in parallel
      const scripts = ['/asr/recorder.js', '/asr/wav.js', '/asr/pcm.js'];
      for (const src of scripts) {
        await loadScript(src);
      }

      return new Promise<void>((resolve, reject) => {
        if (!window.Recorder) {
          reject("Recorder library not loaded");
          return;
        }

        try {
          recorder.value = new window.Recorder({
            type: 'wav',
            sampleRate: 16000,
            bitRate: 16,
            onProcess: (buffers: any[], powerLevel: number, _bufferDuration: number, bufferSampleRate: number) => {
              // Update audio level (0-100)
              audioLevel.value = powerLevel;

              // Calculate Zero Crossing Rate (ZCR) to estimate frequency
              if (buffers.length > 0) {
                const lastBuffer = buffers[buffers.length - 1];
                let zeroCrossings = 0;
                for (let i = 1; i < lastBuffer.length; i++) {
                  if ((lastBuffer[i] >= 0 && lastBuffer[i - 1] < 0) || (lastBuffer[i] < 0 && lastBuffer[i - 1] >= 0)) {
                    zeroCrossings++;
                  }
                }
                // Normalize ZCR roughly (assuming speech max freq around 4000Hz, sample rate 48000 or whatever)
                // Just use a relative scale 0-1
                audioFrequency.value = Math.min(1, zeroCrossings / (lastBuffer.length / 2)); 
              }

              if (isVoiceActive.value && wsConnecter.value && wsConnecter.value.getConnectState()) {
                const data_48k = buffers[buffers.length - 1];
                const array_48k = new Array(data_48k);
                // Downsample to 16k
                const data_16k = window.Recorder.SampleData(array_48k, bufferSampleRate, 16000).data;

                sampleBuf.value = Int16Array.from([...sampleBuf.value, ...data_16k]);

                const chunk_size = 960;
                while (sampleBuf.value.length >= chunk_size) {
                  const sendBuf = sampleBuf.value.slice(0, chunk_size);
                  sampleBuf.value = sampleBuf.value.slice(chunk_size);
                  wsConnecter.value.wsSend(sendBuf);
                }
              }
            }
          });

          recorder.value.open(() => {
            resolve();
          }, (msg: string) => {
            reject(`Recorder open failed: ${msg}`);
          });
        } catch (error) {
          reject(error);
        }
      });
    } catch (err) {
      onError(err as Error);
    }
  };

  const handleWebSocketMessage = (jsonMsg: any) => {
    try {
      const data = JSON.parse(jsonMsg.data);
      
      if (data.mode === "2pass-online") {
        speechRecognitionState.value.pendingOnlineText += data.text;
      } else if (data.mode === "2pass-offline") {
        speechRecognitionState.value.lastRecognizedText += data.text;
        speechRecognitionState.value.pendingOnlineText = '';
      }
    } catch (error) {
      console.error("Failed to parse WebSocket message:", error);
    }
  };

  const initWebSocket = async () => {
    try {
      await loadScript('/asr/wsconnecter.js');
      
      return new Promise<void>((resolve, reject) => {
        if (!window.WSConnecter) {
          reject("WSConnecter library not loaded");
          return;
        }

        if (!serverAddress) {
          reject("ASR Server Address is not configured");
          return;
        }

        try {
          wsConnecter.value = new window.WSConnecter({
            url: serverAddress,
            mode: "2pass",
            useITN: true,
            hotWords: "",
            msgHandle: handleWebSocketMessage,
            onError: (_: any) => {
              stopRecording();
            }
          });

          const result = wsConnecter.value.wsStart();
          if (result === 1) {
            resolve();
          } else {
            reject("Failed to start WebSocket connection");
          }
        } catch (err) {
          reject(err);
        }
      });
    } catch (err) {
      onError(err as Error);
      throw err;
    }
  };

  const waitForWSConnection = async (timeoutMs = 5000): Promise<boolean> => {
    const startTime = Date.now();
    while (Date.now() - startTime < timeoutMs) {
      if (wsConnecter.value && wsConnecter.value.getConnectState()) {
        return true;
      }
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    return false;
  };

  const startRecording = async () => {
    try {
      isConnecting.value = true;
      connectionFailed.value = false;

      EventBus.emit(AUDIO_EVENTS.STOP_TTS);

      if (!recorder.value) {
        await initRecorder();
      }
      if (!wsConnecter.value) {
        await initWebSocket();
      }

      // Wait for WebSocket connection to be established
      const connected = await waitForWSConnection();
      if (!connected) {
        throw new Error("语音识别服务连接出错，请检查服务器配置");
      }

      // Reset state for new recording
      speechRecognitionState.value.pendingOnlineText = '';
      speechRecognitionState.value.lastRecognizedText = '';
      
      recorder.value.start();
      isVoiceActive.value = true;
      onSuccess("Voice recognition started");
    } catch (error) {
      // Clean up error handling
      onError(error instanceof Error ? error.message : String(error));
      isVoiceActive.value = false;
    } finally {
      isConnecting.value = false;
    }
  };

  const stopRecording = () => {
    if (recorder.value) {
        recorder.value.stop((_blob: Blob, _duration: number) => {
        });

      isVoiceActive.value = false;
      onSuccess("Voice recognition stopped");

      // Send remaining buffer
      if (wsConnecter.value) {
        if (wsConnecter.value.getConnectState()) {
          if (sampleBuf.value.length > 0) {
            wsConnecter.value.wsSend(sampleBuf.value);
            sampleBuf.value = new Int16Array();
          }

          const request = {
            "chunk_size": [5, 10, 5],
            "wav_name": "h5",
            "is_speaking": false,
            "chunk_interval": 10,
            "mode": "2pass"
          };
          wsConnecter.value.wsSend(JSON.stringify(request));

          wsConnecter.value.stop();
        }
        wsConnecter.value = null;
      }
    }
  };

  onUnmounted(() => {
    EventBus.off(AUDIO_EVENTS.STOP_ASR, stopAsrHandler);

    if (recorder.value) {
      recorder.value.close();
      recorder.value = null;
    }
    if (wsConnecter.value) {
      wsConnecter.value.stop();
      wsConnecter.value = null;
    }
  });

  return {
    isVoiceActive,
    isConnecting,
    speechRecognitionState,
    startRecording,
    stopRecording,
    audioLevel,
    audioFrequency
  };
};
