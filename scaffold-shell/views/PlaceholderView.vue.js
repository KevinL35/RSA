import { computed } from 'vue';
import { useRoute } from 'vue-router';
import { APP_MENUS } from '../config/menu.config';
const route = useRoute();
const currentTitle = computed(() => {
    for (const item of APP_MENUS) {
        if (item.path === route.path)
            return item.label;
        const child = item.children?.find((x) => x.path === route.path);
        if (child)
            return child.label;
    }
    return '业务模块';
});
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
let __VLS_0;
/** @ts-ignore @type {typeof __VLS_components.elCard | typeof __VLS_components.ElCard | typeof __VLS_components.elCard | typeof __VLS_components.ElCard} */
elCard;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    ...{ class: "view-card" },
}));
const __VLS_2 = __VLS_1({
    ...{ class: "view-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
var __VLS_5 = {};
/** @type {__VLS_StyleScopedClasses['view-card']} */ ;
const { default: __VLS_6 } = __VLS_3.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
(__VLS_ctx.currentTitle);
__VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
(__VLS_ctx.currentTitle);
// @ts-ignore
[currentTitle, currentTitle,];
var __VLS_3;
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
//# sourceMappingURL=PlaceholderView.vue.js.map