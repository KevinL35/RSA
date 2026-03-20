import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { useAuthStore } from '../stores/auth';
const username = ref('');
const password = ref('');
const loading = ref(false);
const router = useRouter();
const auth = useAuthStore();
async function onSubmit() {
    loading.value = true;
    try {
        await auth.login(username.value, password.value);
        router.replace('/insight-analysis');
    }
    catch (e) {
        ElMessage.error(e instanceof Error ? e.message : '登录失败');
    }
    finally {
        loading.value = false;
    }
}
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "login-page" },
});
/** @type {__VLS_StyleScopedClasses['login-page']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div)({
    ...{ class: "login-bg-orb orb-a" },
});
/** @type {__VLS_StyleScopedClasses['login-bg-orb']} */ ;
/** @type {__VLS_StyleScopedClasses['orb-a']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div)({
    ...{ class: "login-bg-orb orb-b" },
});
/** @type {__VLS_StyleScopedClasses['login-bg-orb']} */ ;
/** @type {__VLS_StyleScopedClasses['orb-b']} */ ;
let __VLS_0;
/** @ts-ignore @type {typeof __VLS_components.elCard | typeof __VLS_components.ElCard | typeof __VLS_components.elCard | typeof __VLS_components.ElCard} */
elCard;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
    ...{ class: "card" },
    shadow: "never",
}));
const __VLS_2 = __VLS_1({
    ...{ class: "card" },
    shadow: "never",
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
/** @type {__VLS_StyleScopedClasses['card']} */ ;
const { default: __VLS_5 } = __VLS_3.slots;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "card-title" },
});
/** @type {__VLS_StyleScopedClasses['card-title']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "card-subtitle" },
});
/** @type {__VLS_StyleScopedClasses['card-subtitle']} */ ;
let __VLS_6;
/** @ts-ignore @type {typeof __VLS_components.elForm | typeof __VLS_components.ElForm | typeof __VLS_components.elForm | typeof __VLS_components.ElForm} */
elForm;
// @ts-ignore
const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
    ...{ 'onSubmit': {} },
}));
const __VLS_8 = __VLS_7({
    ...{ 'onSubmit': {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_7));
let __VLS_11;
const __VLS_12 = ({ submit: {} },
    { onSubmit: (__VLS_ctx.onSubmit) });
const { default: __VLS_13 } = __VLS_9.slots;
let __VLS_14;
/** @ts-ignore @type {typeof __VLS_components.elFormItem | typeof __VLS_components.ElFormItem | typeof __VLS_components.elFormItem | typeof __VLS_components.ElFormItem} */
elFormItem;
// @ts-ignore
const __VLS_15 = __VLS_asFunctionalComponent1(__VLS_14, new __VLS_14({
    label: "账号",
}));
const __VLS_16 = __VLS_15({
    label: "账号",
}, ...__VLS_functionalComponentArgsRest(__VLS_15));
const { default: __VLS_19 } = __VLS_17.slots;
let __VLS_20;
/** @ts-ignore @type {typeof __VLS_components.elInput | typeof __VLS_components.ElInput} */
elInput;
// @ts-ignore
const __VLS_21 = __VLS_asFunctionalComponent1(__VLS_20, new __VLS_20({
    modelValue: (__VLS_ctx.username),
    size: "large",
    placeholder: "请输入账号",
}));
const __VLS_22 = __VLS_21({
    modelValue: (__VLS_ctx.username),
    size: "large",
    placeholder: "请输入账号",
}, ...__VLS_functionalComponentArgsRest(__VLS_21));
// @ts-ignore
[onSubmit, username,];
var __VLS_17;
let __VLS_25;
/** @ts-ignore @type {typeof __VLS_components.elFormItem | typeof __VLS_components.ElFormItem | typeof __VLS_components.elFormItem | typeof __VLS_components.ElFormItem} */
elFormItem;
// @ts-ignore
const __VLS_26 = __VLS_asFunctionalComponent1(__VLS_25, new __VLS_25({
    label: "密码",
}));
const __VLS_27 = __VLS_26({
    label: "密码",
}, ...__VLS_functionalComponentArgsRest(__VLS_26));
const { default: __VLS_30 } = __VLS_28.slots;
let __VLS_31;
/** @ts-ignore @type {typeof __VLS_components.elInput | typeof __VLS_components.ElInput} */
elInput;
// @ts-ignore
const __VLS_32 = __VLS_asFunctionalComponent1(__VLS_31, new __VLS_31({
    modelValue: (__VLS_ctx.password),
    size: "large",
    type: "password",
    showPassword: true,
    placeholder: "请输入密码",
}));
const __VLS_33 = __VLS_32({
    modelValue: (__VLS_ctx.password),
    size: "large",
    type: "password",
    showPassword: true,
    placeholder: "请输入密码",
}, ...__VLS_functionalComponentArgsRest(__VLS_32));
// @ts-ignore
[password,];
var __VLS_28;
let __VLS_36;
/** @ts-ignore @type {typeof __VLS_components.elButton | typeof __VLS_components.ElButton | typeof __VLS_components.elButton | typeof __VLS_components.ElButton} */
elButton;
// @ts-ignore
const __VLS_37 = __VLS_asFunctionalComponent1(__VLS_36, new __VLS_36({
    ...{ 'onClick': {} },
    ...{ class: "submit-btn" },
    type: "primary",
    size: "large",
    loading: (__VLS_ctx.loading),
}));
const __VLS_38 = __VLS_37({
    ...{ 'onClick': {} },
    ...{ class: "submit-btn" },
    type: "primary",
    size: "large",
    loading: (__VLS_ctx.loading),
}, ...__VLS_functionalComponentArgsRest(__VLS_37));
let __VLS_41;
const __VLS_42 = ({ click: {} },
    { onClick: (__VLS_ctx.onSubmit) });
/** @type {__VLS_StyleScopedClasses['submit-btn']} */ ;
const { default: __VLS_43 } = __VLS_39.slots;
// @ts-ignore
[onSubmit, loading,];
var __VLS_39;
var __VLS_40;
// @ts-ignore
[];
var __VLS_9;
var __VLS_10;
// @ts-ignore
[];
var __VLS_3;
// @ts-ignore
[];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};
//# sourceMappingURL=LoginView.vue.js.map