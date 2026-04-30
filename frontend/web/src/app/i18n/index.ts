import { createI18n } from 'vue-i18n'
import en from './locales/en'
import zhCN from './locales/zh-CN'

export type AppLocale = 'en' | 'zh-CN'

function readStoredLocale(): AppLocale {
  try {
    const s = localStorage.getItem('rsa_locale')
    if (s === 'en' || s === 'zh-CN') return s
  } catch {
    
  }
  return 'zh-CN'
}

export const i18n = createI18n({
  legacy: false,
  locale: readStoredLocale(),
  fallbackLocale: 'en',
  messages: {
    en,
    'zh-CN': zhCN,
  },
})

export function persistLocale(locale: AppLocale) {
  localStorage.setItem('rsa_locale', locale)
}

export function isEnglishLocale(locale: string): boolean {
  return locale === 'en'
}
