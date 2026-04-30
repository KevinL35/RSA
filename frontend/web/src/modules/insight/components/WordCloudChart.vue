<template>
  <div class="wordcloud-zoom-wrap">
    <div ref="hostRef" class="wordcloud-host" />
  </div>
</template>

<script setup lang="ts">
import * as echarts from 'echarts'
import 'echarts-wordcloud'
import { nextTick, onMounted, onUnmounted, ref, shallowRef, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    
    items: { name: string; value: number; color?: string; dimensionLabel?: string }[]
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
  const palette = props.colors.length > 0 ? props.colors : ['#5470c6', '#91cc75']
  const data = props.items.map((d, i) => {
    const color = d.color?.trim() || palette[i % palette.length]!
    return {
      name: d.name,
      value: d.value,
      textStyle: { color },
    }
  })
  return {
    tooltip: {
      show: true,
      trigger: 'item',
      
      triggerOn: 'mousemove|click',
      showDelay: 0,
      hideDelay: 80,
      confine: true,
      formatter: (raw: unknown) => {
        const p = raw as { dataIndex?: number; name?: string; value?: number }
        const idx = p.dataIndex
        const item = typeof idx === 'number' ? props.items[idx] : undefined
        const name = item?.name ?? p.name ?? ''
        const val = item?.value ?? p.value ?? ''
        const dim = item?.dimensionLabel?.trim()
        
        if (dim) return `${dim}：${val}`
        return name ? `${name}: ${val}` : ''
      },
    },
    series: [
      {
        type: 'wordCloud',
        shape: 'circle',
        left: 'center',
        top: 'center',
        
        width: '98%',
        height: '62%',
        sizeRange: [13, 44],
        
        rotationRange: [0, 0],
        rotationStep: 0,
        gridSize: 6,
        drawOutOfBound: false,
        layoutAnimation: true,
        cursor: 'pointer',
        stateAnimation: {
          duration: 280,
          easing: 'cubicOut',
        },
        textStyle: {
          
          color: palette[0],
        },
        emphasis: {
          focus: 'self',
          blurScope: 'global',
          textStyle: {
            fontWeight: 700,
          },
        },
        blur: {
          textStyle: {
            opacity: 0.28,
          },
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
.wordcloud-zoom-wrap {
  width: 100%;
  height: 100%;
  min-height: 240px;
  padding: 10px;
  box-sizing: border-box;
  overflow: visible;
  



  transition: filter 0.25s ease;
}

.wordcloud-zoom-wrap:hover {
  filter: brightness(1.03);
}

.wordcloud-host {
  width: 100%;
  height: 100%;
  min-height: 220px;
}
</style>
