<template>
  <div class="config-section phrases-config-section">
    <div class="agent-model-section-header">
      <div class="header-text">
        <h3>常用提问</h3>
        <p>配置智能体的常用提问模板，方便快速发起对话</p>
      </div>
      <button v-if="phrases.length > 0" class="header-add-btn" type="button" @click="addPhrase">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
          <path d="M12 5v14M5 12h14"/>
        </svg>
        <span>添加提问</span>
      </button>
    </div>

    <a-form layout="vertical" class="form-content">
      <a-form-item>
        <div class="phrases-panel">
          <Transition name="phrase-state" mode="out-in">
            <!-- 空状态 -->
            <div v-if="phrases.length === 0" key="empty" class="phrases-empty-state">
              <div class="empty-illustration">
                <div class="empty-card empty-card--back"></div>
                <div class="empty-card empty-card--front">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                <div class="empty-spark">+</div>
              </div>
              <p class="empty-title">暂无常用提问</p>
              <p class="empty-desc">添加你经常使用的问题，之后可以一键唤起对话</p>
              <button class="add-btn add-btn--primary" type="button" @click="addPhrase">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                  <path d="M12 5v14M5 12h14"/>
                </svg>
                <span>新建常用提问</span>
              </button>
            </div>

            <!-- 提问列表 -->
            <div v-else key="list" class="phrases-list">
              <TransitionGroup name="phrase-slide" class="phrases-list-body" tag="div">
                <div
                  v-for="(phrase, index) in phrases"
                  :key="index"
                  class="phrase-item"
                >
                  <div class="phrase-leading">
                    <span class="phrase-number">{{ String(index + 1).padStart(2, '0') }}</span>
                  </div>
                  <div class="phrase-editor">
                    <span class="phrase-label">常用提问</span>
                    <input
                      class="phrase-input"
                      :value="phrase"
                      @input="(e: Event) => updatePhrase(index, (e.target as HTMLInputElement).value)"
                      placeholder="例如：帮我总结今天的会议纪要"
                      spellcheck="false"
                    />
                  </div>
                  <button
                    class="phrase-delete"
                    type="button"
                    @click="removePhrase(index)"
                    title="删除"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M18 6L6 18M6 6l12 12"/>
                    </svg>
                  </button>
                </div>
              </TransitionGroup>
            </div>
          </Transition>
        </div>
      </a-form-item>
    </a-form>
  </div>
</template>

<script setup lang="ts">
import NotificationService from '@/utils/NotificationService';

interface Props {
  phrases: string[];
  formErrors: Record<string, boolean>;
}

interface Emits {
  (e: 'update:phrases', value: string[]): void;
  (e: 'update:errors', value: Record<string, boolean>): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const updatePhrase = (index: number, value: string) => {
  const updatedPhrases = [...props.phrases];
  updatedPhrases[index] = value;
  emit('update:phrases', updatedPhrases);
};

const addPhrase = () => {
  const lastPhrase = props.phrases[props.phrases.length - 1];
  if (lastPhrase !== undefined && !lastPhrase.trim()) {
    NotificationService.warning('请先填写当前常用提问');
    return;
  }
  const updatedPhrases = [...props.phrases];
  updatedPhrases.push('');
  emit('update:phrases', updatedPhrases);
};

const removePhrase = (index: number) => {
  const updatedPhrases = [...props.phrases];
  updatedPhrases.splice(index, 1);
  emit('update:phrases', updatedPhrases);
};
</script>

<style scoped lang="scss">
.phrases-config-section {
  flex: 1;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;

  .agent-model-section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 20px;

    .header-text {
      flex: 1;
      min-width: 0;

      h3 {
        font-size: 16px;
        font-weight: 500;
        color: #262626;
        margin: 0 0 4px 0;
      }

      p {
        font-size: 13px;
        color: #86909c;
        margin: 0;
      }
    }

    .header-add-btn {
      flex-shrink: 0;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 14px;
      border-radius: 10px;
      border: 1.5px solid #e8eef5;
      background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
      color: #5a6a7a;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);

      svg {
        display: block;
      }

      span {
        line-height: 1;
      }

      &:hover {
        border-color: #1677ff;
        color: #1677ff;
        background: #f0f7ff;
        box-shadow: 0 2px 8px -2px rgba(22, 119, 255, 0.25);
      }

      &:active {
        transform: scale(0.96);
      }
    }
  }
}

.form-content {
  flex: 1;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;

  :deep(.ant-form) {
    flex: 1;
    height: 100%;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  :deep(.ant-form-item) {
    flex: 1;
    width: 100%;
    min-height: 0;
    display: flex;
    flex-direction: column;
    margin-bottom: 0;
  }

  :deep(.ant-form-item-label) {
    display: none;
  }

  :deep(.ant-form-item-row),
  :deep(.ant-form-item-control),
  :deep(.ant-form-item-control-input),
  :deep(.ant-form-item-control-input-content) {
    flex: 1;
    height: 100%;
    width: 100%;
    align-self: stretch;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
}

.phrases-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding-top: 14px;
  padding-bottom: 14px;
}

.phrases-empty-state {
  flex: 1;
  width: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
}

.empty-illustration {
  position: relative;
  width: 92px;
  height: 72px;
  margin-bottom: 18px;
}

.empty-card {
  position: absolute;
  width: 66px;
  height: 48px;
  border-radius: 16px;
  border: 1px solid rgba(147, 197, 253, 0.78);
  background: #ffffff;
}

.empty-card--back {
  top: 4px;
  left: 8px;
  transform: rotate(-8deg);
  background: linear-gradient(135deg, #eff6ff, #ffffff);
}

.empty-card--front {
  top: 13px;
  left: 18px;
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 12px;
  box-shadow: 0 18px 34px -25px rgba(37, 99, 235, 0.75);

  span {
    height: 4px;
    border-radius: 999px;
    background: #bfdbfe;
  }

  span:nth-child(1) {
    width: 34px;
    background: #60a5fa;
  }

  span:nth-child(2) {
    width: 42px;
  }

  span:nth-child(3) {
    width: 24px;
  }
}

.empty-spark {
  position: absolute;
  right: 0;
  bottom: 2px;
  width: 26px;
  height: 26px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  font-size: 18px;
  font-weight: 600;
  background: #3187ff;
  box-shadow: 0 10px 20px -12px rgba(37, 99, 235, 0.85);
  padding-bottom: 4px;
}

.empty-title {
  margin: 0 0 6px;
  color: #1e293b;
  font-size: 15px;
  font-weight: 650;
}

.empty-desc {
  margin: 0 0 22px;
  color: #64748b;
  font-size: 13px;
}

.phrases-list {
  width: 100%;
  min-height: 0;
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 10px;
}

.phrases-list-body {
  min-height: 0;
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 2px 2px 2px 0;
}

.phrase-item {
  position: relative;
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr) 32px;
  align-items: center;
  min-height: 62px;
  padding: 10px 10px 10px 12px;
  border: 1px solid #e6edf6;
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;

  &::after {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: inherit;
    pointer-events: none;
    background: linear-gradient(135deg, rgba(22, 119, 255, 0.08), transparent 38%);
    opacity: 0;
    transition: opacity 0.2s ease;
  }

  &:hover,
  &:focus-within {
    transform: translateY(-1px);
    border-color: #bcd7ff;
    box-shadow: 0 10px 24px -22px rgba(22, 119, 255, 0.62);

    &::after {
      opacity: 1;
    }

    .phrase-delete {
      opacity: 1;
    }
  }

  &:focus-within {
    border-color: #69a7ff;
  }
}

.phrase-leading {
  display: flex;
  align-items: center;
  gap: 8px;
}

.phrase-number {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #1677ff;
  font-size: 11px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  background: #edf5ff;
}

.phrase-editor {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.phrase-label {
  color: #94a3b8;
  font-size: 12px;
  line-height: 1;
}

.phrase-input {
  width: 100%;
  min-width: 0;
  border: none;
  outline: none;
  padding: 0;
  color: #1f2937;
  background: transparent;
  font-size: 13px;
  line-height: 1.5;

  &::placeholder {
    color: #b8c2d1;
  }
}

.phrase-delete {
  position: relative;
  z-index: 1;
  width: 30px;
  height: 30px;
  border: 1px solid transparent;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.76);
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s ease;

  &:hover {
    color: #f5222d;
    border-color: #ffd6d9;
    background: #fff1f0;
  }
}

.add-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  border-radius: 12px;
  border: 1.5px solid #e8eef5;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  color: #5a6a7a;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background: linear-gradient(135deg, rgba(22, 119, 255, 0.06), transparent 50%);
    opacity: 0;
    transition: opacity 0.25s ease;
  }

  &::after {
    content: '';
    position: absolute;
    left: 50%;
    top: 50%;
    width: 0;
    height: 0;
    border-radius: 50%;
    background: rgba(22, 119, 255, 0.08);
    transform: translate(-50%, -50%);
    transition: width 0.4s ease, height 0.4s ease;
  }

  svg {
    position: relative;
    z-index: 1;
    transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  }

  span {
    position: relative;
    z-index: 1;
  }

  &:hover {
    border-color: #bcd7ff;
    color: #1677ff;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px -4px rgba(22, 119, 255, 0.25);

    &::before {
      opacity: 1;
    }

    svg {
      transform: rotate(90deg);
    }
  }

  &:active {
    transform: translateY(0);
    
    &::after {
      width: 200px;
      height: 200px;
    }
  }

  &--primary {
    min-width: 75px;
    height: 36px;
    padding: 0 16px;
    border: none;
    border-radius: 10px;
    color: #ffffff;
    background: linear-gradient(135deg, #1677ff 0%, #4096ff 100%);
    box-shadow: 0 2px 8px -2px rgba(22, 119, 255, 0.35);
    font-size: 13px;
    font-weight: 500;
    transition: box-shadow 0.25s ease, background 0.25s ease, color 0.25s ease, filter 0.25s ease;

    &::before {
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.15), transparent 50%);
    }

    &:hover {
      color: #ffffff;
      box-shadow: 0 4px 16px -4px rgba(22, 119, 255, 0.45);
      transform: translateY(-1px);

      svg {
        transform: none;
      }
    }
  }
}

.phrase-slide-enter-active {
  transition: all 0.28s ease;
}

.phrase-slide-leave-active {
  transition: all 0.2s ease;
}

.phrase-slide-enter-from {
  opacity: 0;
  transform: translateY(-8px) scale(0.98);
}

.phrase-slide-leave-to {
  opacity: 0;
  transform: translateX(16px) scale(0.98);
}

/* 空状态与列表切换过渡 */
.phrase-state-enter-active,
.phrase-state-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.phrase-state-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

.phrase-state-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.97);
}

/* 按钮入场淡入 */
@keyframes btn-fade-in {
  0% {
    opacity: 0;
    transform: translateY(6px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

.phrase-state-enter-active .add-btn--primary {
  animation: btn-fade-in 0.25s ease 0.12s both;
}
</style>
