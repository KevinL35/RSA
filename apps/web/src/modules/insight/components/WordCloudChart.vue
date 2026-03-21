<template>
  <div ref="hostRef" class="wordcloud-host" />
</template>

<script setup lang="ts">
import * as echarts from 'echarts'
import 'echarts-wordcloud'
import { nextTick, onMounted, onUnmounted, ref, shallowRef, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    items: { name: string; value: number }[]
    colors?: string[]
  }>(),
  {
    colors: () => ['#5470c6', '#91cc75', '#fac858', '#ee6666'],
  },
)

const hostRef = ref<HTMLElement | null>(null)
const chartRef = shallowRef<echarts.ECharts | null>(null)
let resizeObserver: ResizeObserver | null = null

function buildOption() {
  const data = props.items.map((d) => ({ name: d.name, value: d.value }))
  const palette = props.colors.length > 0 ? props.colors : ['#5470c6', '#91cc75']
  return {
    tooltip: {
      show: true,
      formatter: (p: { name?: string; value?: number }) =>
        p?.name != null ? `${p.name}: ${p.value ?? ''}` : '',
    },
    series: [
      {
        type: 'wordCloud',
        shape: 'circle',
        left: 'center',
        top: 'center',
        /** 扁长区域 + 低纵向占比 → 布局更偏横向排布（ellipticity ∝ height/width） */
        width: '98%',
        height: '62%',
        sizeRange: [12, 40],
        /** 全部水平方向展示 */
        rotationRange: [0, 0],
        rotationStep: 0,
        gridSize: 6,
        drawOutOfBound: false,
        layoutAnimation: true,
        textStyle: {
          color: () => palette[Math.floor(Math.random() * palette.length)]!,
        },
        emphasis: {
          focus: 'self',
          textStyle: { textShadowBlur: 8, textShadowColor: 'rgba(0,0,0,0.35)' },
        },
        data,
      },
    ],
  }
}

function apply() {
  const chart = chartRef.value
  if (!chart) return
  if (props.items.length === 0) {
    chart.clear()
    return
  }
  chart.setOption(buildOption() as echarts.EChartsCoreOption, true)
}

onMounted(async () => {
  await nextTick()
  const el = hostRef.value
  if (!el) return
  chartRef.value = echarts.init(el)
  apply()
  resizeObserver = new ResizeObserver(() => chartRef.value?.resize())
  resizeObserver.observe(el)
})

watch(
  () => [props.items, props.colors] as const,
  () => {
    apply()
  },
  { deep: true },
)

onUnmounted(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
  chartRef.value?.dispose()
  chartRef.value = null
})
</script>

<style scoped>
.wordcloud-host {
  width: 100%;
  height: 100%;
  min-height: 240px;
}
</style>
