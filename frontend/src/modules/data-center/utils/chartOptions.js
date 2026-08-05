import { compactAxisNumber } from './formatters'

export function buildMarketChartOptions({ bars, indicators, priceLayers, subChart, chartHeight }) {
  const dates = bars.map((item) => item.trade_date)
  const candle = bars.map((item) => [item.open, item.close, item.low, item.high])
  const volume = bars.map((item) => item.volume)
  const series = [
    {
      name: 'K线',
      type: 'candlestick',
      data: candle,
      itemStyle: { color: '#d85a4a', color0: '#2f7d5b', borderColor: '#d85a4a', borderColor0: '#2f7d5b' }
    }
  ]

  addPriceLayer(series, indicators, priceLayers, 'ma5', 'MA5', '#4d7ea8')
  addPriceLayer(series, indicators, priceLayers, 'ma10', 'MA10', '#b7791f')
  addPriceLayer(series, indicators, priceLayers, 'ma20', 'MA20', '#2f7d5b')
  addPriceLayer(series, indicators, priceLayers, 'ma60', 'MA60', '#6b5b95')
  if (priceLayers.includes('boll')) {
    series.push(lineSeries('BOLL上轨', indicators?.boll?.upper || [], '#8b8f9a', 'dashed'))
    series.push(lineSeries('BOLL中轨', indicators?.boll?.mid || [], '#59656f', 'dotted'))
    series.push(lineSeries('BOLL下轨', indicators?.boll?.lower || [], '#8b8f9a', 'dashed'))
  }

  const legend = series.map((item) => item.name)
  const sliderHeight = 36
  const sliderBottom = 8
  const lowerPlotBottom = chartHeight - sliderHeight - sliderBottom - 30
  const priceTop = 52
  const availablePlotHeight = Math.max(400, lowerPlotBottom - priceTop)
  const hasIndicatorSubChart = subChart !== 'volume'
  const priceHeight = Math.round(availablePlotHeight * (hasIndicatorSubChart ? 0.56 : 0.68))
  const volumeTop = priceTop + priceHeight + 24
  const remainingLowerHeight = lowerPlotBottom - volumeTop
  const volumeHeight = hasIndicatorSubChart
    ? Math.max(70, Math.round((remainingLowerHeight - 20) * 0.42))
    : Math.max(112, remainingLowerHeight)
  const gridBase = { left: 10, right: 24, containLabel: true }
  const yAxis = [createYAxis(0)]
  const xAxis = [createDateAxis(dates, 0, false)]
  const grid = [{ ...gridBase, top: priceTop, height: priceHeight }]

  grid.push({ ...gridBase, top: volumeTop, height: volumeHeight })
  xAxis.push(createDateAxis(dates, 1, subChart === 'volume'))
  yAxis.push(createYAxis(1, compactAxisNumber))
  series.push({ name: '成交量', type: 'bar', data: volume, xAxisIndex: 1, yAxisIndex: 1, itemStyle: { color: '#b7c5bd' } })
  legend.push('成交量')

  if (subChart !== 'volume') {
    const subChartTop = volumeTop + volumeHeight + 20
    grid.push({ ...gridBase, top: subChartTop, height: Math.max(72, lowerPlotBottom - subChartTop) })
    xAxis.push(createDateAxis(dates, 2, true))
    yAxis.push(createYAxis(2))
    if (subChart === 'rsi') {
      series.push({ ...lineSeries('RSI14', indicators?.rsi14 || [], '#a35f2d'), xAxisIndex: 2, yAxisIndex: 2 })
      legend.push('RSI14')
    }
    if (subChart === 'macd') {
      const macd = indicators?.macd || {}
      series.push({ name: 'MACD', type: 'bar', data: macd.macd || [], xAxisIndex: 2, yAxisIndex: 2, itemStyle: { color: '#8ea89a' } })
      series.push({ ...lineSeries('DIF', macd.dif || [], '#4d7ea8'), xAxisIndex: 2, yAxisIndex: 2 })
      series.push({ ...lineSeries('DEA', macd.dea || [], '#b7791f'), xAxisIndex: 2, yAxisIndex: 2 })
      legend.push('MACD', 'DIF', 'DEA')
    }
  }

  return {
    animation: false,
    backgroundColor: '#ffffff',
    tooltip: { trigger: 'axis', confine: true, axisPointer: { type: 'cross' } },
    legend: { data: legend, top: 8, textStyle: { color: '#425047' } },
    grid,
    xAxis,
    yAxis,
    dataZoom: [
      { type: 'inside', xAxisIndex: xAxis.map((_, index) => index) },
      {
        type: 'slider',
        show: true,
        xAxisIndex: xAxis.map((_, index) => index),
        left: 88,
        right: 88,
        bottom: sliderBottom,
        height: sliderHeight,
        brushSelect: false,
        showDetail: true,
        showDataShadow: true,
        handleLabel: { show: true },
        labelFormatter: (_value, valueStr) => valueStr || '',
        backgroundColor: '#f4f7f5',
        borderColor: '#d6dfd7',
        borderRadius: 4,
        fillerColor: 'rgba(77, 126, 168, 0.16)',
        dataBackground: {
          lineStyle: { color: '#9baba1', width: 1 },
          areaStyle: { color: 'rgba(183, 197, 189, 0.2)' }
        },
        selectedDataBackground: {
          lineStyle: { color: '#4d7ea8', width: 1.2 },
          areaStyle: { color: 'rgba(77, 126, 168, 0.22)' }
        },
        handleSize: '112%',
        handleStyle: {
          color: '#ffffff',
          borderColor: '#4d7ea8',
          borderWidth: 2,
          shadowBlur: 4,
          shadowColor: 'rgba(36, 61, 48, 0.14)'
        },
        textStyle: {
          color: '#425047',
          fontSize: 11,
          backgroundColor: '#ffffff',
          borderColor: '#d6dfd7',
          borderWidth: 1,
          borderRadius: 4,
          padding: [3, 6]
        },
        emphasis: {
          handleLabel: { show: true },
          handleStyle: { color: '#ffffff', borderColor: '#2f7d5b', borderWidth: 2 }
        }
      }
    ],
    series
  }
}

function addPriceLayer(series, indicators, priceLayers, key, name, color) {
  if (priceLayers.includes(key)) {
    series.push(lineSeries(name, indicators?.[key] || [], color))
  }
}

function lineSeries(name, data, color, type = 'solid') {
  return {
    name,
    type: 'line',
    data,
    smooth: true,
    showSymbol: false,
    lineStyle: { width: 1.5, color, type }
  }
}

function createDateAxis(dates, gridIndex, showLabels) {
  return {
    type: 'category',
    data: dates,
    gridIndex,
    scale: true,
    boundaryGap: true,
    axisLine: { lineStyle: { color: '#cbd6ce' } },
    axisTick: { show: showLabels, alignWithLabel: true },
    axisLabel: {
      color: '#66746b',
      fontSize: 11,
      margin: 10,
      hideOverlap: true,
      showMinLabel: true,
      showMaxLabel: true,
      alignMinLabel: 'left',
      alignMaxLabel: 'right',
      show: showLabels
    }
  }
}

function createYAxis(gridIndex, formatter) {
  return {
    gridIndex,
    scale: true,
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: {
      color: '#66746b',
      fontSize: 11,
      margin: 12,
      ...(formatter ? { formatter } : {})
    },
    axisPointer: { label: { show: false } },
    splitLine: { lineStyle: { color: '#eef1ec' } }
  }
}
