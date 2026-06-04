/* Map Panel — Leaflet 渲染、节点交互、按天切换 */

let map = null;
let currentMapData = null;
let dayFeatureGroups = {};
let allMarkers = [];  // {marker, spot, color}

function initMap() {
  if (map) return;
  map = L.map('mapContainer', {
    center: [30.24, 120.15],
    zoom: 12,
    zoomControl: false,
  });
  L.tileLayer('https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', {
    attribution: '高德地图', maxZoom: 18,
  }).addTo(map);
  L.control.zoom({ position: 'bottomright' }).addTo(map);
  // 点击地图空白 → 关闭面板
  map.on('click', () => closeInfoPanel());
  if (currentMapData) renderMap(currentMapData);
}

function renderMap(data) {
  currentMapData = data;
  if (!map) return;

  // 隐藏占位提示
  const placeholder = document.getElementById('mapPlaceholder');
  if (placeholder) placeholder.style.display = 'none';

  // 清除旧图层
  Object.values(dayFeatureGroups).forEach(fg => map.removeLayer(fg));
  dayFeatureGroups = {};
  allMarkers = [];
  closeInfoPanel();

  const { spots, routes, center } = data;
  if (!spots || spots.length === 0) return;

  if (center && center.length === 2 && center[0] !== 39.9) {
    map.setView(center, 12);
  }

  const dayGroups = {};
  spots.forEach(s => { const d = s.day || 1; if (!dayGroups[d]) dayGroups[d] = []; dayGroups[d].push(s); });
  const maxDay = Math.max(...Object.keys(dayGroups).map(Number));
  const colors = ['#E74C3C', '#3498DB', '#2ECC71', '#9B59B6', '#F39C12', '#1ABC9C'];

  // 更新 Tab
  const tabs = document.getElementById('mapTabs');
  tabs.innerHTML = '<button class="map-tab active" data-day="all">全部</button>';
  for (let d = 1; d <= maxDay; d++) {
    if (dayGroups[d]) tabs.innerHTML += `<button class="map-tab" data-day="${d}">第${d}天</button>`;
  }
  tabs.querySelectorAll('.map-tab').forEach(btn => {
    btn.addEventListener('click', () => filterMapDay(btn.dataset.day));
  });

  // 为每天创建 FeatureGroup
  Object.entries(dayGroups).forEach(([day, daySpots]) => {
    const color = colors[(Number(day) - 1) % colors.length];
    const fg = L.featureGroup();

    daySpots.forEach(spot => {
      const { lat, lng, name, order, time } = spot;

      // 单一 CircleMarker（可点击）
      const marker = L.circleMarker([lat, lng], {
        radius: 10, color: '#fff', weight: 3,
        fillColor: color, fillOpacity: 0.85,
      });
      marker.on('click', (e) => { L.DomEvent.stopPropagation(e); showInfoPanel(spot, color); });
      marker.addTo(fg);

      // 单一标签：序号 + 名称 + 时间
      const labelHtml = `<div style="
        background:rgba(255,255,255,0.95);border-radius:10px;
        padding:3px 7px;font-size:11px;font-weight:600;
        white-space:nowrap;box-shadow:0 2px 6px rgba(0,0,0,0.18);
        border-left:3px solid ${color};cursor:pointer;
        pointer-events:auto;
      "><span style="display:inline-flex;align-items:center;justify-content:center;
        background:${color};color:#fff;width:16px;height:16px;border-radius:50%;
        font-size:9px;margin-right:4px;">${order}</span>${name.substring(0,6)}${time ? '<br><span style=\'color:#8E8E93;font-weight:400;font-size:10px;margin-left:20px\'>'+time+'</span>' : ''}</div>`;

      const labelIcon = L.divIcon({ className: '', html: labelHtml, iconSize: [0, 0], iconAnchor: [10, -20] });
      const labelMarker = L.marker([lat, lng], { icon: labelIcon, interactive: true });
      labelMarker.on('click', (e) => { L.DomEvent.stopPropagation(e); showInfoPanel(spot, color); });
      labelMarker.addTo(fg);

      allMarkers.push({ marker, labelMarker, spot, color, fg });
    });

    fg.addTo(map);
    dayFeatureGroups[day] = fg;
  });

  // 初始适应范围
  const firstFg = dayFeatureGroups[1] || Object.values(dayFeatureGroups)[0];
  if (firstFg) map.fitBounds(firstFg.getBounds().pad(0.3));

  // 路线连线
  if (routes && routes.length > 0) {
    routes.forEach(r => {
      if (r.coords && r.coords.length >= 2) {
        const lineColor = r.color || colors[(Number(r.day) - 1) % colors.length];
        const line = L.polyline(r.coords, {
          color: lineColor, weight: 4, opacity: 0.5, dashArray: '8 4',
        });
        const targetFg = dayFeatureGroups[r.day];
        if (targetFg) targetFg.addLayer(line); else line.addTo(map);
      }
    });
  }
}

function filterMapDay(day) {
  document.querySelectorAll('.map-tab').forEach(t => t.classList.remove('active'));
  document.querySelector(`[data-day="${day}"]`)?.classList.add('active');
  closeInfoPanel();

  if (day === 'all') {
    Object.values(dayFeatureGroups).forEach(fg => { if (!map.hasLayer(fg)) fg.addTo(map); });
  } else {
    Object.entries(dayFeatureGroups).forEach(([d, fg]) => {
      if (d === day) {
        if (!map.hasLayer(fg)) fg.addTo(map);
        map.fitBounds(fg.getBounds().pad(0.2));
      } else {
        if (map.hasLayer(fg)) map.removeLayer(fg);
      }
    });
  }
}

function showInfoPanel(spot, color) {
  const panel = document.getElementById('mapInfoPanel');
  const nameEl = document.getElementById('infoSpotName');
  const tableEl = document.getElementById('infoTable');

  // 高亮当前标记
  allMarkers.forEach(({ marker }) => marker.setStyle({ weight: 3, radius: 10 }));
  const hit = allMarkers.find(m => m.spot.name === spot.name && m.spot.day === spot.day);
  if (hit) hit.marker.setStyle({ weight: 5, radius: 14 });

  nameEl.innerHTML = `<span style="display:inline-block;width:22px;height:22px;background:${color};color:#fff;border-radius:50%;text-align:center;line-height:22px;font-size:10px;margin-right:6px;">${spot.order}</span> ${spot.name}`;

  const rows = [
    ['序号', `第 ${spot.order} 个景点 (第 ${spot.day} 天)`],
    ['时间', spot.time || '未指定'],
    ['活动', spot.activity || '未指定'],
    ['交通', spot.transport || '未指定'],
    ['费用', spot.cost || '未指定'],
    ['坐标', `${spot.lat.toFixed(4)}, ${spot.lng.toFixed(4)}`],
  ];

  tableEl.innerHTML = rows.map(([label, value]) => `
    <tr><td>${label}</td><td>${value}</td></tr>
  `).join('');

  panel.style.display = 'block';
}

function closeInfoPanel() {
  document.getElementById('mapInfoPanel').style.display = 'none';
  // 取消高亮
  allMarkers.forEach(({ marker }) => marker.setStyle({ weight: 3, radius: 10 }));
}
