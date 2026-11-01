<template>
  <div class="audio-playing-icon">
    <span class="dot" :class="{ 'loading': !isPlaying, 'playing': isPlaying }"></span>
    <span 
      v-for="i in 10" 
      :key="i"
      class="bar"
      :class="{ 'animating': !isPlaying }"
      :style="getBarStyle(i - 1)"
    ></span>
    <span class="dot" :class="{ 'loading': !isPlaying, 'playing': isPlaying }"></span>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';

const props = defineProps<{
  analyser?: AnalyserNode | null;
  isPlaying?: boolean;
}>();

const barHeights = ref<number[]>(new Array(10).fill(20));
let animationFrameId: number | null = null;

const updateVisualization = () => {
  if (props.isPlaying && props.analyser) {
    const dataArray = new Uint8Array(props.analyser.frequencyBinCount);
    props.analyser.getByteFrequencyData(dataArray);
    
    // Voice range is mostly in lower frequencies (0-4kHz).
    // fftSize=256 -> binCount=128. SampleRate~44k -> MaxFreq~22k.
    // Each bin is ~172Hz.
    // To cover ~5kHz, we need ~30 bins.
    // Let's focus on the first 30 bins for 10 bars (3 bins per bar).
    const step = 3;
    
    for (let i = 0; i < 10; i++) {
      let sum = 0;
      for (let j = 0; j < step; j++) {
        // Use an offset to skip very low rumble if needed, but 0 is fine
        const index = i * step + j;
        if (index < dataArray.length) {
          sum += dataArray[index];
        }
      }
      const avg = sum / step;
      // Map 0-255 to 20%-100% height
      // 20% base height + (avg/255 * 80%)
      barHeights.value[i] = 20 + (avg / 255) * 80;
    }
    
    animationFrameId = requestAnimationFrame(updateVisualization);
  }
};

watch(() => props.isPlaying, (newVal) => {
  if (newVal) {
    updateVisualization();
  } else {
    if (animationFrameId) {
      cancelAnimationFrame(animationFrameId);
      animationFrameId = null;
    }
  }
});

onMounted(() => {
  if (props.isPlaying) {
    updateVisualization();
  }
});

onUnmounted(() => {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
  }
});

const getBarStyle = (index: number) => {
  if (props.isPlaying) {
    return {
      height: `${barHeights.value[index]}%`,
      transition: 'height 0.1s ease'
    };
  }
  return {}; // Use CSS defined heights/animations
};
</script>

<style scoped>
.audio-playing-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1px;
  height: 14px;
}

.dot {
  width: 2px;
  height: 2px;
  border-radius: 50%;
  flex-shrink: 0;
  margin: 0 4px; /* Add slight spacing around dots */
}

.dot.loading {
  background-color: #3b82f6; /* Blue for loading */
  box-shadow: 0 0 4px #3b82f6;
  animation: pulse-dot 1s infinite;
}

.dot.playing {
  background-color: #10b981; /* Green for playing */
  box-shadow: 0 0 4px #10b981;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 0.5; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.2); }
}

.bar {
  width: 2px;
  background-color: currentColor;
  border-radius: 1px;
}

/* Animation styles for loading state */
.bar.animating {
  animation: wave 1s ease-in-out infinite;
}

.bar.animating:nth-child(1) { height: 30%; animation-delay: 0.0s; }
.bar.animating:nth-child(2) { height: 50%; animation-delay: 0.1s; }
.bar.animating:nth-child(3) { height: 80%; animation-delay: 0.2s; }
.bar.animating:nth-child(4) { height: 100%; animation-delay: 0.3s; }
.bar.animating:nth-child(5) { height: 80%; animation-delay: 0.4s; }
.bar.animating:nth-child(6) { height: 60%; animation-delay: 0.5s; }
.bar.animating:nth-child(7) { height: 40%; animation-delay: 0.4s; }
.bar.animating:nth-child(8) { height: 60%; animation-delay: 0.3s; }
.bar.animating:nth-child(9) { height: 80%; animation-delay: 0.2s; }
.bar.animating:nth-child(10) { height: 50%; animation-delay: 0.1s; }

@keyframes wave {
  0%, 100% {
    height: 20%;
  }
  50% {
    height: 100%;
  }
}
</style>
