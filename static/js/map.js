
// Khởi tạo bản đồ
const map = L.map("map").setView([10.762622, 106.660172], 12);

// Layer nền
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap contributors"
}).addTo(map);

// Load dữ liệu GIS (GeoJSON)
fetch("/static/data/poi.geojson")
    .then(response => response.json())
    .then(data => {
        L.geoJSON(data, {
            onEachFeature: function (feature, layer) {
                if (feature.properties && feature.properties.name) {
                    layer.bindPopup(feature.properties.name);
                }
            }
        }).addTo(map);
    })
    .catch(error => {
        console.error("Lỗi load GeoJSON:", error);
    });
