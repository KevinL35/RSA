import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessageBox } from 'element-plus';
import { APP_MENUS } from '../config/menu.config';
import { useAuthStore } from '../stores/auth';
const collapsed = ref(false);
const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const menus = APP_MENUS;
const activePath = computed(() => route.path);
const defaultOpeneds = computed(() => {
    const parent = menus.find((item) => item.children?.some((child) => child.path === route.path));
    return parent ? [parent.key] : [];
});
const currentTitle = computed(() => {
    for (const item of menus) {
        if (item.path === route.path)
            return item.label;
        const child = item.children?.find((x) => x.path === route.path);
        if (child)
            return child.label;
    }
    return '工作台';
});
const closeMenuSvg = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/><path d="m16 15-3-3 3-3"/></svg>';
const openMenuSvg = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M15 3v18"/><path d="m8 9 3 3-3 3"/></svg>';
const logoutSvg = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/></svg>';
function onSelect(path) {
    router.push(path);
}
async function onLogout() {
    await ElMessageBox.confirm('确认退出登录？', '提示', { type: 'warning' });
    auth.logout();
    router.replace('/login');
}
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['sidebar']} */ ;
/** @type {__VLS_StyleScopedClasses['brand-text']} */ ;
/** @type {__VLS_StyleScopedClasses['brand-text']} */ ;
/** @type {__VLS_StyleScopedClasses['shell-menu']} */ ;
/** @type {__VLS_StyleScopedClasses['shell-menu']} */ ;
/** @type {__VLS_StyleScopedClasses['el-menu-item']} */ ;
/** @type {__VLS_StyleScopedClasses['shell-menu']} */ ;
/** @type {__VLS_StyleScopedClasses['el-menu-item']} */ ;
/** @type {__VLS_StyleScopedClasses['shell-menu']} */ ;
/** @type {__VLS_StyleScopedClasses['shell-menu']} */ ;
/** @type {__VLS_StyleScopedClasses['el-sub-menu__title']} */ ;
/** @type {__VLS_StyleScopedClasses['shell-menu']} */ ;
/** @type {__VLS_StyleScopedClasses['el-sub-menu__title']} */ ;
/** @type {__VLS_StyleScopedClasses['shell-menu']} */ ;
/** @type {__VLS_StyleScopedClasses['el-sub-menu']} */ ;
/** @type {__VLS_StyleScopedClasses['el-menu-item']} */ ;
/** @type {__VLS_StyleScopedClasses['menu-icon']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "layout-shell" },
});
/** @type {__VLS_StyleScopedClasses['layout-shell']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.aside, __VLS_intrinsics.aside)({
    ...{ class: "sidebar" },
    ...{ class: ({ collapsed: __VLS_ctx.collapsed }) },
});
/** @type {__VLS_StyleScopedClasses['sidebar']} */ ;
/** @type {__VLS_StyleScopedClasses['collapsed']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "sidebar-top" },
});
/** @type {__VLS_StyleScopedClasses['sidebar-top']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "brand-mark" },
});
/** @type {__VLS_StyleScopedClasses['brand-mark']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "brand-text" },
});
__VLS_asFunctionalDirective(__VLS_directives.vShow, {})(null, { ...__VLS_directiveBindingRestFields, value: (!__VLS_ctx.collapsed) }, null, null);
/** @type {__VLS_StyleScopedClasses['brand-text']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
__VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
let __VLS_0;
/** @ts-ignore @type {typeof __VLS_components.elScrollbar | typeof __VLS_components.ElScrollbar | typeof __VLS_components.elScrollbar | typeof __VLS_components.ElScrollbar} */
elScrollbar;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    ...{ class: "menu-wrap" },
}));
const __VLS_2 = __VLS_1({
    ...{ class: "menu-wrap" },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
/** @type {__VLS_StyleScopedClasses['menu-wrap']} */ ;
const { default: __VLS_5 } = __VLS_3.slots;
let __VLS_6;
/** @ts-ignore @type {typeof __VLS_components.elMenu | typeof __VLS_components.ElMenu | typeof __VLS_components.elMenu | typeof __VLS_components.ElMenu} */
elMenu;
// @ts-ignore
const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
    ...{ 'onSelect': {} },
    defaultActive: (__VLS_ctx.activePath),
    defaultOpeneds: (__VLS_ctx.defaultOpeneds),
    collapse: (__VLS_ctx.collapsed),
    collapseTransition: (false),
    ...{ class: "shell-menu" },
}));
const __VLS_8 = __VLS_7({
    ...{ 'onSelect': {} },
    defaultActive: (__VLS_ctx.activePath),
    defaultOpeneds: (__VLS_ctx.defaultOpeneds),
    collapse: (__VLS_ctx.collapsed),
    collapseTransition: (false),
    ...{ class: "shell-menu" },
}, ...__VLS_functionalComponentArgsRest(__VLS_7));
let __VLS_11;
const __VLS_12 = ({ select: {} },
    { onSelect: (__VLS_ctx.onSelect) });
/** @type {__VLS_StyleScopedClasses['shell-menu']} */ ;
const { default: __VLS_13 } = __VLS_9.slots;
for (const [item] of __VLS_vFor((__VLS_ctx.menus))) {
    (item.key);
    if (item.children?.length) {
        let __VLS_14;
        /** @ts-ignore @type {typeof __VLS_components.elSubMenu | typeof __VLS_components.ElSubMenu | typeof __VLS_components.elSubMenu | typeof __VLS_components.ElSubMenu} */
        elSubMenu;
        // @ts-ignore
        const __VLS_15 = __VLS_asFunctionalComponent1(__VLS_14, new __VLS_14({
            index: (item.key),
        }));
        const __VLS_16 = __VLS_15({
            index: (item.key),
        }, ...__VLS_functionalComponentArgsRest(__VLS_15));
        const { default: __VLS_19 } = __VLS_17.slots;
        {
            const { title: __VLS_20 } = __VLS_17.slots;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span)({
                ...{ class: "menu-icon" },
            });
            __VLS_asFunctionalDirective(__VLS_directives.vHtml, {})(null, { ...__VLS_directiveBindingRestFields, value: (item.icon) }, null, null);
            /** @type {__VLS_StyleScopedClasses['menu-icon']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
            (item.label);
            // @ts-ignore
            [collapsed, collapsed, collapsed, activePath, defaultOpeneds, onSelect, menus,];
        }
        for (const [child] of __VLS_vFor((item.children))) {
            let __VLS_21;
            /** @ts-ignore @type {typeof __VLS_components.elMenuItem | typeof __VLS_components.ElMenuItem | typeof __VLS_components.elMenuItem | typeof __VLS_components.ElMenuItem} */
            elMenuItem;
            // @ts-ignore
            const __VLS_22 = __VLS_asFunctionalComponent1(__VLS_21, new __VLS_21({
                key: (child.key),
                index: (child.path),
            }));
            const __VLS_23 = __VLS_22({
                key: (child.key),
                index: (child.path),
            }, ...__VLS_functionalComponentArgsRest(__VLS_22));
            const { default: __VLS_26 } = __VLS_24.slots;
            (child.label);
            // @ts-ignore
            [];
            var __VLS_24;
            // @ts-ignore
            [];
        }
        // @ts-ignore
        [];
        var __VLS_17;
    }
    else {
        let __VLS_27;
        /** @ts-ignore @type {typeof __VLS_components.elMenuItem | typeof __VLS_components.ElMenuItem | typeof __VLS_components.elMenuItem | typeof __VLS_components.ElMenuItem} */
        elMenuItem;
        // @ts-ignore
        const __VLS_28 = __VLS_asFunctionalComponent1(__VLS_27, new __VLS_27({
            index: (item.path),
        }));
        const __VLS_29 = __VLS_28({
            index: (item.path),
        }, ...__VLS_functionalComponentArgsRest(__VLS_28));
        const { default: __VLS_32 } = __VLS_30.slots;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span)({
            ...{ class: "menu-icon" },
        });
        __VLS_asFunctionalDirective(__VLS_directives.vHtml, {})(null, { ...__VLS_directiveBindingRestFields, value: (item.icon) }, null, null);
        /** @type {__VLS_StyleScopedClasses['menu-icon']} */ ;
        {
            const { title: __VLS_33 } = __VLS_30.slots;
            (item.label);
            // @ts-ignore
            [];
        }
        // @ts-ignore
        [];
        var __VLS_30;
    }
    // @ts-ignore
    [];
}
// @ts-ignore
[];
var __VLS_9;
var __VLS_10;
// @ts-ignore
[];
var __VLS_3;
__VLS_asFunctionalElement1(__VLS_intrinsics.main, __VLS_intrinsics.main)({
    ...{ class: "main" },
});
/** @type {__VLS_StyleScopedClasses['main']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
    ...{ class: "topbar" },
});
/** @type {__VLS_StyleScopedClasses['topbar']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "topbar-left" },
});
/** @type {__VLS_StyleScopedClasses['topbar-left']} */ ;
let __VLS_34;
/** @ts-ignore @type {typeof __VLS_components.elButton | typeof __VLS_components.ElButton | typeof __VLS_components.elButton | typeof __VLS_components.ElButton} */
elButton;
// @ts-ignore
const __VLS_35 = __VLS_asFunctionalComponent1(__VLS_34, new __VLS_34({
    ...{ 'onClick': {} },
    ...{ class: "icon-btn" },
}));
const __VLS_36 = __VLS_35({
    ...{ 'onClick': {} },
    ...{ class: "icon-btn" },
}, ...__VLS_functionalComponentArgsRest(__VLS_35));
let __VLS_39;
const __VLS_40 = ({ click: {} },
    { onClick: (...[$event]) => {
            __VLS_ctx.collapsed = !__VLS_ctx.collapsed;
            // @ts-ignore
            [collapsed, collapsed,];
        } });
/** @type {__VLS_StyleScopedClasses['icon-btn']} */ ;
const { default: __VLS_41 } = __VLS_37.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.span)({
    ...{ class: "menu-icon" },
});
__VLS_asFunctionalDirective(__VLS_directives.vHtml, {})(null, { ...__VLS_directiveBindingRestFields, value: (__VLS_ctx.collapsed ? __VLS_ctx.openMenuSvg : __VLS_ctx.closeMenuSvg) }, null, null);
/** @type {__VLS_StyleScopedClasses['menu-icon']} */ ;
// @ts-ignore
[collapsed, openMenuSvg, closeMenuSvg,];
var __VLS_37;
var __VLS_38;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "page-title" },
});
/** @type {__VLS_StyleScopedClasses['page-title']} */ ;
(__VLS_ctx.currentTitle);
let __VLS_42;
/** @ts-ignore @type {typeof __VLS_components.elButton | typeof __VLS_components.ElButton | typeof __VLS_components.elButton | typeof __VLS_components.ElButton} */
elButton;
// @ts-ignore
const __VLS_43 = __VLS_asFunctionalComponent1(__VLS_42, new __VLS_42({
    ...{ 'onClick': {} },
    ...{ class: "logout-btn" },
}));
const __VLS_44 = __VLS_43({
    ...{ 'onClick': {} },
    ...{ class: "logout-btn" },
}, ...__VLS_functionalComponentArgsRest(__VLS_43));
let __VLS_47;
const __VLS_48 = ({ click: {} },
    { onClick: (__VLS_ctx.onLogout) });
/** @type {__VLS_StyleScopedClasses['logout-btn']} */ ;
const { default: __VLS_49 } = __VLS_45.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.span)({
    ...{ class: "menu-icon" },
});
__VLS_asFunctionalDirective(__VLS_directives.vHtml, {})(null, { ...__VLS_directiveBindingRestFields, value: (__VLS_ctx.logoutSvg) }, null, null);
/** @type {__VLS_StyleScopedClasses['menu-icon']} */ ;
// @ts-ignore
[currentTitle, onLogout, logoutSvg,];
var __VLS_45;
var __VLS_46;
__VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
    ...{ class: "content" },
});
/** @type {__VLS_StyleScopedClasses['content']} */ ;
let __VLS_50;
/** @ts-ignore @type {typeof __VLS_components.routerView | typeof __VLS_components.RouterView} */
routerView;
// @ts-ignore
const __VLS_51 = __VLS_asFunctionalComponent1(__VLS_50, new __VLS_50({}));
const __VLS_52 = __VLS_51({}, ...__VLS_functionalComponentArgsRest(__VLS_51));
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
//# sourceMappingURL=MainLayout.vue.js.map