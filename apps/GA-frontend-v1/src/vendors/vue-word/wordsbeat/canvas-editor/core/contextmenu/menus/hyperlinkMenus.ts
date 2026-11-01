import { INTERNAL_CONTEXT_MENU_KEY } from '../../../dataset/constant/ContextMenu'
import { EDITOR_COMPONENT } from '../../../dataset/constant/Editor'
import { ElementType } from '../../../dataset/enum/Element'
import { EditorComponent } from '../../../dataset/enum/Editor'
import {
  IContextMenuContext,
  IRegisterContextMenu
} from '../../../interface/contextmenu/ContextMenu'
import { Command } from '../../command/Command'
import { h } from 'vue'
import { Input, Modal } from 'ant-design-vue'
const {
  HYPERLINK: { DELETE, CANCEL, EDIT }
} = INTERNAL_CONTEXT_MENU_KEY

export const hyperlinkMenus: IRegisterContextMenu[] = [
  {
    key: DELETE,
    i18nPath: 'contextmenu.hyperlink.delete',
    when: payload => {
      return (
        !payload.isReadonly &&
        payload.startElement?.type === ElementType.HYPERLINK
      )
    },
    callback: (command: Command) => {
      command.executeDeleteHyperlink()
    }
  },
  {
    key: CANCEL,
    i18nPath: 'contextmenu.hyperlink.cancel',
    when: payload => {
      return (
        !payload.isReadonly &&
        payload.startElement?.type === ElementType.HYPERLINK
      )
    },
    callback: (command: Command) => {
      command.executeCancelHyperlink()
    }
  },
  {
    key: EDIT,
    i18nPath: 'contextmenu.hyperlink.edit',
    when: payload => {
      return (
        !payload.isReadonly &&
        payload.startElement?.type === ElementType.HYPERLINK
      )
    },
    callback: (command: Command, context: IContextMenuContext) => {
      let urlValue = context.startElement?.url || ''
      const uniqueWrapClass = `wordsbeat-link-dialog-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
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
      setTimeout(() => setEditorComponentAttr(), 0)
      Modal.confirm({
        title: command.executeTranslate('contextmenu.hyperlink.edit'),
        icon: () => null,
        wrapClassName,
        zIndex: 30000,
        okText: '确定',
        cancelText: '取消',
        content: h(Input, {
          value: urlValue,
          placeholder: '请输入链接地址',
          autofocus: true,
          'onUpdate:value': (value: string) => {
            urlValue = value || ''
          }
        }),
        onOk: () => {
          const nextUrl = urlValue.trim()
          if (nextUrl) {
            command.executeEditHyperlink(nextUrl)
          }
        }
      })
    }
  }
]
