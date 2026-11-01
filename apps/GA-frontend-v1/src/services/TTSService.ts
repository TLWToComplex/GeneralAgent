import { ref } from 'vue';
import EventBus, { AUDIO_EVENTS } from '@/utils/EventBus';
import { getTtsServer } from '@/utils/RuntimeConfig';
import NotificationService from '@/utils/NotificationService';

class TTSService {
  private ws: WebSocket | null = null;
  private audioQueue: Blob[] = [];
  private isPlaying = ref(false);
  private currentMessageId = ref<string | null>(null);
  private currentAudio: HTMLAudioElement | null = null;
  private audioContext: AudioContext | null = null;
  public readonly analyser = ref<AnalyserNode | null>(null);
  private source: MediaElementAudioSourceNode | null = null;
  private gainNode: GainNode | null = null;
  private readonly FADE_TIME = 0.5;
  private totalChunks = 0;
  private receivedChunks = 0;

  constructor() {
    // 监听停止TTS事件
    // 使用 import 的 EventBus 和 AUDIO_EVENTS
    EventBus.on(AUDIO_EVENTS.STOP_TTS, () => {
      this.stop();
    });
  }

  /**
   * 初始化 AudioContext
   */
  private initAudioContext() {
    if (!this.audioContext) {
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      this.audioContext = new AudioContextClass();
      this.gainNode = this.audioContext.createGain();
      this.analyser.value = this.audioContext.createAnalyser();
      this.analyser.value.fftSize = 256; // 设置FFT大小，决定了频域数据的精细度
    }
    if (this.audioContext.state === 'suspended') {
      this.audioContext.resume();
    }
  }

  /**
   * 连接 WebSocket
   */
  private connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }

      // 只要不是 OPEN，就重新创建连接 (如果是 CONNECTING，可能需要等待，这里简单处理为覆盖)
      if (this.ws) {
        this.ws.close();
        this.ws = null;
      }

      const server = getTtsServer();
      if (!server) {
        reject(new Error("TTS Server not configured"));
        return;
      }
      const ws = new WebSocket(server);
      this.ws = ws;
      this.ws.binaryType = 'blob';

      let isResolved = false;

      ws.onopen = () => {
        if (!isResolved) {
          isResolved = true;
          resolve();
        }
      };

      ws.onerror = (error) => {
        console.error('TTS WebSocket error:', error);
        NotificationService.error('语音合成服务连接出错，请检查服务器配置');
        this.stop();
        if (!isResolved) {
          isResolved = true;
          reject(error);
        }
      };

      ws.onclose = () => {
        if (this.ws === ws) {
          this.ws = null;
        }
        // 如果连接关闭且尚未 resolve (说明连接建立失败或立即关闭)，则 reject
        if (!isResolved) {
          isResolved = true;
          reject(new Error('WebSocket closed before connection established'));
        }
      };

      ws.onmessage = (event) => {
        this.handleMessage(event);
      };
    });
  }

  /**
   * 处理收到的消息 (音频数据)
   */
  private handleMessage(event: MessageEvent) {
    if (event.data instanceof Blob) {
      this.audioQueue.push(event.data);
      this.receivedChunks++;
      this.playNext();
    }
  }

  /**
   * 播放队列中的下一个音频
   */
  private playNext() {
    if (this.currentAudio && !this.currentAudio.paused) {
      return;
    }

    if (this.audioQueue.length === 0) {
      // 如果接收到的音频数量少于发送的文本片段数量，说明还有音频未到达，保持播放状态
      if (this.receivedChunks < this.totalChunks) {
        // 队列为空但还有未接收的音频，进入 buffering 状态
        // 设置 isPlaying = false 以显示 loading 动画
        this.isPlaying.value = false;
        return;
      }
      this.isPlaying.value = false;
      this.currentMessageId.value = null; // 队列为空且所有音频已播放，重置当前消息ID
      return;
    }

    this.isPlaying.value = true;
    const blob = this.audioQueue.shift();
    if (!blob) return;

    const url = URL.createObjectURL(blob);
    this.currentAudio = new Audio(url);
    this.currentAudio.crossOrigin = "anonymous"; // 防止跨域问题

    // 连接到 AudioContext
    this.initAudioContext();
    if (this.audioContext && this.analyser.value && this.gainNode) {
      this.source = this.audioContext.createMediaElementSource(this.currentAudio);
      // 连接路径: Source -> Gain -> Analyser -> Destination
      this.source.connect(this.gainNode);
      this.gainNode.connect(this.analyser.value);
      this.analyser.value.connect(this.audioContext.destination);
    }
    
    this.currentAudio.onended = () => {
      URL.revokeObjectURL(url);
      this.currentAudio = null;
      this.playNext();
    };

    this.currentAudio.onerror = (e) => {
      console.error('Audio playback error:', e);
      URL.revokeObjectURL(url);
      this.currentAudio = null;
      this.playNext();
    };

    this.currentAudio.play().then(() => {
      if (this.audioContext && this.gainNode && this.currentAudio) {
        const currentTime = this.audioContext.currentTime;
        const duration = this.currentAudio.duration;
        // 如果无法获取时长，则只应用淡入
        const fadeTime = Number.isFinite(duration) ? Math.min(this.FADE_TIME, duration / 2) : this.FADE_TIME;

        // 淡入效果
        this.gainNode.gain.cancelScheduledValues(currentTime);
        this.gainNode.gain.setValueAtTime(0, currentTime);
        this.gainNode.gain.linearRampToValueAtTime(1, currentTime + fadeTime);

        // 如果时长有效，预设淡出效果
        if (Number.isFinite(duration)) {
          this.gainNode.gain.setValueAtTime(1, currentTime + duration - fadeTime);
          this.gainNode.gain.linearRampToValueAtTime(0, currentTime + duration);
        }
      }
    }).catch(err => {
      console.error('Play failed:', err);
      this.playNext();
    });
  }

  /**
   * 停止播放并断开连接
   */
  public stop() {
    // 1. Send stop command if connected
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify({ stop: true }));
      } catch (e) {
        console.error('Failed to send stop command:', e);
      }
    }

    // 2. Close WebSocket
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    // 清空队列，防止继续播放
    this.audioQueue = [];

    // 3. Stop audio playback with fade out
    if (this.currentAudio && !this.currentAudio.paused && this.audioContext && this.gainNode) {
      // 防止自动播放下一首
      this.currentAudio.onended = null;
      
      const currentTime = this.audioContext.currentTime;
      // 取消可能的自然淡出计划
      this.gainNode.gain.cancelScheduledValues(currentTime);
      // 从当前音量开始快速淡出 (300ms)
      this.gainNode.gain.setValueAtTime(this.gainNode.gain.value, currentTime);
      this.gainNode.gain.linearRampToValueAtTime(0, currentTime + 0.3);
      
      // 延迟执行真正的停止
      setTimeout(() => { // 使用 arrow function 保持 this 上下文
        this.doStopCleanup();
      }, 300);
    } else {
      this.doStopCleanup();
    }
  }

  private doStopCleanup() {
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio = null;
    }
    if (this.source) {
      this.source.disconnect();
      this.source = null;
    }
    // 不要关闭 audioContext，复用它
    
    this.audioQueue = [];
    this.isPlaying.value = false;
    this.currentMessageId.value = null;
    this.totalChunks = 0;
    this.receivedChunks = 0;
  }

  /**
   * 朗读文本
   * @param text 要朗读的文本
   * @param messageId 消息ID，用于标识当前正在朗读的消息
   */
  public async speak(text: string, messageId: string) {
    try {
      // 发送停止ASR信号
      EventBus.emit(AUDIO_EVENTS.STOP_ASR);

      // 如果点击的是当前正在播放的消息，则停止
      if (this.currentMessageId.value === messageId && this.isPlaying.value) {
        this.stop();
        return;
      }

      this.stop(); // 停止之前的朗读
      
      const chunks = this.splitText(text);
      if (chunks.length === 0) return;

      this.totalChunks = chunks.length;
      this.receivedChunks = 0;

      this.currentMessageId.value = messageId;
      this.initAudioContext(); // 确保在用户交互时恢复 AudioContext
      await this.connect();

      // 如果当前消息ID变了（说明被停止或切换了），则不再发送
      if (this.currentMessageId.value !== messageId) {
        return;
      }

      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        // 不要立即设置 isPlaying = true，等待收到音频数据开始播放时再设置
        // 这样前端会因为 isPlaying = false 但 currentMessageId 有值而显示 loading 动画
        this.ws.send(JSON.stringify(chunks));
      } else {
        throw new Error('WebSocket connection failed or not open');
      }
    } catch (error) {
      console.error('Failed to start TTS:', error);
      this.isPlaying.value = false;
      this.currentMessageId.value = null;
    }
  }

  /**
   * 文本切分算法
   * 按照一般人类阅读的长度进行切分
   */
  private splitText(text: string): string[] {
    if (!text) return [];
    const cleanedText = this.sanitizeForTts(text);
    if (!cleanedText) return [];

    const MAX_CHUNK_LENGTH = 20; // 理想的最大长度
    
    // 标点符号作为切分点，增加顿号、逗号和冒号以支持更短的切分
    const splitRegex = /([。！？；，：、\.\!\?\;\,\:\n]+)/;
    
    const rawSegments = cleanedText.split(splitRegex);
    const chunks: string[] = [];
    let currentChunk = '';

    for (let i = 0; i < rawSegments.length; i++) {
      const segment = rawSegments[i];
      
      // 如果是标点符号，追加到当前 chunk
      if (splitRegex.test(segment)) {
        currentChunk += segment;
        continue;
      }

      // 如果当前 chunk 加上新片段太长，先保存当前 chunk
      if (currentChunk.length + segment.length > MAX_CHUNK_LENGTH) {
        if (currentChunk) {
          chunks.push(currentChunk);
          currentChunk = '';
        }
      }

      currentChunk += segment;

      // 如果当前 chunk 已经足够长（且不是因为刚追加了标点），也可以考虑切分
      // 但为了保持句子完整性，我们尽量只在遇到标点后切分，
      // 除非 segment 本身就超长（例如很长的无标点文本），那就强制切分
      if (currentChunk.length > MAX_CHUNK_LENGTH) {
         chunks.push(currentChunk);
         currentChunk = '';
      }
    }

    if (currentChunk) {
      chunks.push(currentChunk);
    }

    return chunks.filter(c => c.trim().length > 0);
  }

  private sanitizeForTts(text: string): string {
    let sanitized = text;
    sanitized = sanitized.replace(/```[\s\S]*?```/g, '【代码请查看原文】');
    sanitized = sanitized.replace(/`[^`\n]+`/g, '【代码请查看原文】');
    sanitized = sanitized.replace(/<code[\s\S]*?<\/code>/gi, '【代码请查看原文】');
    sanitized = sanitized.replace(/<table[\s\S]*?<\/table>/gi, '【表格请查看原文】');
    sanitized = this.removeMarkdownTables(sanitized);
    sanitized = sanitized.replace(/\n{3,}/g, '\n\n');
    return sanitized.trim();
  }

  private removeMarkdownTables(text: string): string {
    const lines = text.split('\n');
    const result: string[] = [];
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      const nextLine = lines[i + 1];
      if (this.isTableRow(line) && this.isTableSeparator(nextLine)) {
        i += 2;
        while (i < lines.length && this.isTableRow(lines[i])) {
          i += 1;
        }
        const last = result[result.length - 1]?.trim();
        if (last !== '【表格请查看原文】') {
          result.push('【表格请查看原文】');
        }
        continue;
      }
      result.push(line);
      i += 1;
    }
    return result.join('\n');
  }

  private isTableRow(line?: string): boolean {
    if (!line) return false;
    const pipeCount = (line.match(/\|/g) || []).length;
    return pipeCount >= 2;
  }

  private isTableSeparator(line?: string): boolean {
    if (!line) return false;
    return /^(\s*\|?\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
  }

  public get isSpeaking() {
    return this.isPlaying;
  }

  public get currentPlayingMessageId() {
    return this.currentMessageId;
  }
}

export default new TTSService();
