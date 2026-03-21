import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    allowedRoles?: ('admin' | 'operator' | 'readonly')[]
  }
}
