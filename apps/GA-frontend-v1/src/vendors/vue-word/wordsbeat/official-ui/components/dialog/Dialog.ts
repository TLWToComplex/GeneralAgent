import { h, reactive, ref, type CSSProperties, type VNode } from 'vue'
import { Form, Input, InputNumber, Modal, Select } from 'ant-design-vue'
import { EditorComponent, EDITOR_COMPONENT } from '../../../canvas-editor'

export interface IDialogData {
  type: string
  label?: string
  name: string
  value?: string
  options?: { label: string; value: string }[]
  placeholder?: string
  width?: number
  height?: number
  required?: boolean
}

export interface IDialogConfirm {
  name: string
  value: string
}

export interface IDialogOptions {
  onClose?: () => void
  onCancel?: () => void
  onConfirm?: (payload: IDialogConfirm[]) => void
  title: string
  data: IDialogData[]
}

export class Dialog {
  private options: IDialogOptions

  constructor(options: IDialogOptions) {
    this.options = options
    this._render()
  }

  private _render() {
    const { title, data, onClose, onCancel, onConfirm } = this.options
    const state = reactive<Record<string, string>>({})
    const formRef = ref<any>(null)
    data.forEach(item => {
      state[item.name] = item.value || ''
    })

    const uniqueWrapClass = `wordsbeat-antdv-dialog-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    const wrapClassName = `wordsbeat-confirm-modal ${uniqueWrapClass}`

    const setEditorComponentAttr = () => {
      const wrap = document.querySelector<HTMLElement>(`.${uniqueWrapClass}`)
      if (!wrap) return
      wrap.setAttribute(EDITOR_COMPONENT, EditorComponent.COMPONENT)
      const root = wrap.closest('.ant-modal-root') as HTMLElement | null
      root?.setAttribute(EDITOR_COMPONENT, EditorComponent.COMPONENT)
      root?.querySelectorAll<HTMLElement>('.ant-modal, .ant-modal-mask').forEach(el => {
        el.setAttribute(EDITOR_COMPONENT, EditorComponent.COMPONENT)
      })
    }

    const toCssSize = (value?: number): string | undefined =>
      value ? `${value}px` : undefined

    const textLikeTypes = new Set([
      'text',
      'password',
      'search',
      'email',
      'url',
      'tel'
    ])
    const nativeTypes = new Set(['color', 'date', 'time', 'datetime-local'])
    const requiredMessage = (item: IDialogData) => {
      const prefix = item.type === 'select' ? '请选择' : '请输入'
      return `${prefix}${item.label || item.name}`
    }

    const renderField = (item: IDialogData): VNode => {
      const controlStyle: CSSProperties = {
        width: toCssSize(item.width) || '100%',
        ...(item.height ? { height: toCssSize(item.height) } : {})
      }
      if (item.type === 'select') {
        return h(Select, {
          value: state[item.name],
          options: (item.options || []).map(opt => ({ label: opt.label, value: opt.value })),
          style: controlStyle,
          onChange: (value: unknown) => {
            state[item.name] =
              typeof value === 'string'
                ? value
                : value === null || value === undefined
                  ? ''
                  : String(value)
          }
        })
      }
      if (item.type === 'textarea') {
        return h(Input.TextArea, {
          value: state[item.name],
          placeholder: item.placeholder || '',
          style: controlStyle,
          'onUpdate:value': (value: string) => {
            state[item.name] = value || ''
          }
        })
      }
      if (item.type === 'number') {
        return h(InputNumber, {
          value: state[item.name] === '' ? undefined : Number(state[item.name]),
          style: controlStyle,
          onChange: (value: unknown) => {
            state[item.name] =
              value === null || value === undefined || value === ''
                ? ''
                : String(value)
          }
        })
      }
      const inputType = nativeTypes.has(item.type)
        ? item.type
        : (textLikeTypes.has(item.type) || item.type === 'input' ? 'text' : 'text')
      return h('input', {
        type: inputType,
        value: state[item.name],
        placeholder: item.placeholder || '',
        style: {
          ...controlStyle,
          border: '1px solid #d9d9d9',
          borderRadius: '6px',
          padding: '4px 11px',
          boxSizing: 'border-box'
        } as CSSProperties,
        onInput: (evt: Event) => {
          state[item.name] = (evt.target as HTMLInputElement).value || ''
        }
      })
    }

    const content = h(
      Form,
      {
        ref: formRef,
        model: state,
        layout: 'horizontal',
        requiredMark: true,
        labelCol: { style: { width: '90px', textAlign: 'left' } as CSSProperties },
        wrapperCol: { style: { flex: 1 } as CSSProperties },
        style: { marginTop: '8px' } as CSSProperties
      },
      {
        default: () =>
          data.map(item =>
            h(
              Form.Item,
              {
                label: item.label,
                name: item.name,
                rules: item.required
                  ? [{ required: true, whitespace: true, message: requiredMessage(item), trigger: ['change', 'blur'] }]
                  : [],
                ...(item.label
                  ? {}
                  : {
                      labelCol: { style: { width: '0px', marginRight: '0px' } as CSSProperties },
                      wrapperCol: { style: { flex: 1, maxWidth: '100%' } as CSSProperties }
                    })
              },
              { default: () => [renderField(item)] }
            )
          )
      }
    )

    setTimeout(() => setEditorComponentAttr(), 0)
    Modal.confirm({
      title,
      icon: () => null,
      content,
      centered: true,
      closable: true,
      maskClosable: false,
      keyboard: true,
      zIndex: 30000,
      wrapClassName,
      okText: '确定',
      cancelText: '取消',
      onOk: async () => {
        try {
          await formRef.value?.validate?.()
        } catch (err) {
          return Promise.reject(err)
        }
        onConfirm?.(
          data.map<IDialogConfirm>(item => ({
            name: item.name,
            value: state[item.name] || ''
          }))
        )
      },
      onCancel: () => {
        onCancel?.()
      },
      afterClose: () => {
        onClose?.()
      }
    })
  }
}
