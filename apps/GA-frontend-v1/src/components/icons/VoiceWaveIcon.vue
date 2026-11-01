<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="currentColor"
    v-bind="$attrs"
  >
    <rect class="wave-bar" :class="{ loading: props.loading }" x="4" :y="12 - bar1Height / 2" width="2" :height="bar1Height" rx="1" />
    <rect class="wave-bar" :class="{ loading: props.loading }" x="9" :y="12 - bar2Height / 2" width="2" :height="bar2Height" rx="1" />
    <rect class="wave-bar" :class="{ loading: props.loading }" x="14" :y="12 - bar3Height / 2" width="2" :height="bar3Height" rx="1" />
    <rect class="wave-bar" :class="{ loading: props.loading }" x="19" :y="12 - bar4Height / 2" width="2" :height="bar4Height" rx="1" />
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(defineProps<{
  level?: number; // Audio level 0-100
  frequency?: number; // Approximate frequency metric 0-1
  loading?: boolean;
}>(), {
  level: 0,
  frequency: 0.5,
  loading: false
});

// Calculate bar heights based on audio level with some randomness for visual effect
const calculateHeight = (maxDynamicHeight: number, frequencyBias: number) => {
  if (props.loading) return 10;
  
  // Lower silence threshold for better sensitivity
  if (props.level < 1.5) return 4;
  
  // Adjusted amplification:
  // Formula: Base 20% + (Input * 3.0) -> capped at 100%
  // Increased base and multiplier for "slightly larger" amplitude
  const amplified = Math.min(100, 20 + props.level * 3.0); 
  const ratio = amplified / 100;
  
  // Apply frequency bias
  // If frequencyBias > 0, it responds more to high freq (ZCR)
  // If frequencyBias < 0, it responds more to low freq (1 - ZCR)
  // We make the bias stronger: range 0.5x to 1.5x
  let freqFactor = 1.0;
  if (frequencyBias > 0) {
    // High freq bar: if freq is 1.0 -> 1.5x boost. If freq is 0.0 -> 0.5x penalty.
    freqFactor = 0.5 + (props.frequency * 1.0); 
  } else if (frequencyBias < 0) {
    // Low freq bar: if freq is 0.0 -> 1.5x boost. If freq is 1.0 -> 0.5x penalty.
    freqFactor = 0.5 + ((1 - props.frequency) * 1.0);
  }

  // Multiplicative Randomness ("The Perfect Fix")
  // Instead of just adding a random jitter on top, we multiply the potential height by a random factor.
  // This ensures that even at constant high volume, the bars have very different heights relative to each other.
  // Range: 0.5 to 1.3 (Large variance, slightly higher floor)
  const randomFactor = 0.5 + (Math.random() * 0.8);

  // Combine: Ratio (Volume) * FreqFactor (Pitch) * RandomFactor (Noise)
  // This creates a "Jagged" look where bars are rarely the same height
  const finalScale = ratio * freqFactor * randomFactor;

  return 4 + (finalScale * maxDynamicHeight);
};

// Adjusted max heights to prevent clipping (viewBox is 24px height)
// Max total height ~= 4 + maxDynamicHeight
// Pass a unique seed or just rely on the function call to generate unique random values
// Frequency Bias: -1 (Low/Bass) to 1 (High/Treble)
const bar1Height = computed(() => calculateHeight(10, -1.0)); // Bass-heavy
const bar2Height = computed(() => calculateHeight(14, -0.5)); // Mid-Low
const bar3Height = computed(() => calculateHeight(16, 0.5));  // Mid-High
const bar4Height = computed(() => calculateHeight(12, 1.0));  // Treble-heavy

</script>

<style scoped>
.wave-bar {
  transition: all 0.1s ease-out;
}

.wave-bar.loading {
  transform-box: fill-box;
  transform-origin: 50% 50%;
  animation: wave-loading 1s infinite ease-in-out;
}

.wave-bar.loading:nth-child(1) { animation-delay: 0s; }
.wave-bar.loading:nth-child(2) { animation-delay: 0.15s; }
.wave-bar.loading:nth-child(3) { animation-delay: 0.3s; }
.wave-bar.loading:nth-child(4) { animation-delay: 0.45s; }

@keyframes wave-loading {
  0%, 100% { transform: scaleY(0.4); }
  50% { transform: scaleY(1.2); }
}
</style>
