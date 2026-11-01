import { createApp } from 'vue'
import { createPinia } from 'pinia'

import EmbeddedApp from './EmbeddedApp.vue'

import 'prosemirror-view/style/prosemirror.css'
import 'animate.css'
import '@/assets/styles/prosemirror.scss'
import '@/assets/styles/global.scss'
import '@/assets/styles/font.scss'

import Directive from '@/directive'

const app = createApp(EmbeddedApp)
app.use(Directive)
app.use(createPinia())
app.mount('#app')
