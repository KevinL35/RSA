import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import './styles.css'
import router from './app/router'
import { i18n } from './app/i18n'

createApp(App).use(i18n).use(router).use(ElementPlus).mount('#app')
