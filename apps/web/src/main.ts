import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import './styles.css'
import router from './app/router'

createApp(App).use(router).use(ElementPlus).mount('#app')
