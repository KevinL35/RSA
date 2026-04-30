<template>
  <div ref="hostRef" class="trend-host" />
</template>

<script setup lang="ts">
import * as echarts from 'echarts'
import { nextTick, onMounted, onUnmounted, ref, shallowRef, watch } from 'vue'

export type TrendPoint = { date: string; count: number }

const props = defineProps<{
  points: TrendPoint[]
}>()

const hostRef = ref<HTMLElement | null>(null)
const chartRef = shallowRef<echarts.ECharts | null>(null)
let resizeObserver: ResizeObserver | null = null

function buildOption(): echarts.EChartsCoreOption {
  const dates = props.points.map((p) => p.date)
  const counts = props.points.map((p) => p.count)
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'line' },
    },
    grid: { left: 48, right: 24, top: 28, bottom: 40 },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLabel: { rotate: dates.length > 10 ? 35 : 0, fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { type: 'dashed', opacity: 0.35 } },
    },
    series: [
      {
        type: 'line',
        smooth: 0.35,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { width: 2, color: '#2563eb' },
        itemStyle: { color: '#2563eb' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(37, 99, 235, 0.22)' },
            { offset: 1, color: 'rgba(37, 99, 235, 0.02)' },
          ]),
        },
        data: counts,
      },
    ],
  }
}

function apply() {
  const chart = chartRef.value
  if (!chart) return
  if (props.points.length === 0) {
    chart.clear()
    return
  }
  chart.setOption(buildOption(), true)
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
  () => props.points,
  () => apply(),
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
.trend-host {
  width: 100%;
  height: 280px;
  min-height: 240px;
}
</style>
