/**
 * ==============================================================================
 * ADMIN DASHBOARD JAVASCRIPT MODULE
 * Scope: Enterprise Admin Dashboard only
 * Handles sidebar interactions, real Chart.js rendering, and live table search
 * ==============================================================================
 */

(function () {
    'use strict';

    // Wait for DOM
    document.addEventListener('DOMContentLoaded', function () {
        initSidebar();
        initCharts();
        initLiveTableFilter();
    });

    /**
     * 1. SIDEBAR TOGGLE & STATE PERSISTENCE
     */
    function initSidebar() {
        const appWrapper = document.querySelector('.admin-app-wrapper');
        const desktopToggle = document.getElementById('adminSidebarToggle');
        const mobileToggle = document.getElementById('adminMobileToggle');
        const backdrop = document.getElementById('adminSidebarBackdrop');

        if (!appWrapper) return;

        // Restore desktop collapse state from localStorage
        const isCollapsed = localStorage.getItem('admin_sidebar_collapsed') === 'true';
        if (isCollapsed && window.innerWidth > 768) {
            appWrapper.classList.add('sidebar-collapsed');
        }

        // Desktop Toggle
        if (desktopToggle) {
            desktopToggle.addEventListener('click', function () {
                appWrapper.classList.toggle('sidebar-collapsed');
                const collapsed = appWrapper.classList.contains('sidebar-collapsed');
                localStorage.setItem('admin_sidebar_collapsed', collapsed ? 'true' : 'false');
            });
        }

        // Mobile Drawer Toggle
        if (mobileToggle) {
            mobileToggle.addEventListener('click', function () {
                appWrapper.classList.toggle('mobile-sidebar-open');
            });
        }

        // Close mobile drawer on backdrop click
        if (backdrop) {
            backdrop.addEventListener('click', function () {
                appWrapper.classList.remove('mobile-sidebar-open');
            });
        }
    }

    /**
     * 2. INITIALIZE CHART.JS WITH REAL DATABASE DATA
     */
    function initCharts() {
        if (typeof Chart === 'undefined') {
            console.warn('Chart.js is not loaded yet.');
            return;
        }

        const dataPayload = window.ADMIN_DASHBOARD_DATA;
        if (!dataPayload) return;

        // --- Chart 1: Revenue & Order Count Trend ---
        const trendCanvas = document.getElementById('adminTrendChart');
        if (trendCanvas && dataPayload.trendLabels && dataPayload.trendLabels.length > 0) {
            const ctx = trendCanvas.getContext('2d');

            // Create gradient for revenue fill
            const revGradient = ctx.createLinearGradient(0, 0, 0, 300);
            revGradient.addColorStop(0, 'rgba(37, 99, 235, 0.22)');
            revGradient.addColorStop(1, 'rgba(37, 99, 235, 0.00)');

            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: dataPayload.trendLabels,
                    datasets: [
                        {
                            label: 'Doanh thu GMV (VNĐ)',
                            data: dataPayload.trendRevenue,
                            borderColor: '#2563eb',
                            backgroundColor: revGradient,
                            borderWidth: 2.5,
                            fill: true,
                            tension: 0.35,
                            pointBackgroundColor: '#2563eb',
                            pointBorderColor: '#ffffff',
                            pointBorderWidth: 2,
                            pointRadius: 4,
                            pointHoverRadius: 6,
                            yAxisID: 'yRev'
                        },
                        {
                            label: 'Số lượng đơn hàng',
                            data: dataPayload.trendOrders,
                            borderColor: '#10b981',
                            backgroundColor: 'rgba(16, 185, 129, 0.85)',
                            borderWidth: 1.5,
                            type: 'bar',
                            borderRadius: 6,
                            maxBarThickness: 28,
                            yAxisID: 'yOrders'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    plugins: {
                        legend: {
                            position: 'top',
                            align: 'end',
                            labels: {
                                boxWidth: 12,
                                usePointStyle: true,
                                font: {
                                    family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                                    size: 12,
                                    weight: '600'
                                },
                                color: '#475569'
                            }
                        },
                        tooltip: {
                            backgroundColor: '#0f172a',
                            titleColor: '#ffffff',
                            bodyColor: '#e2e8f0',
                            padding: 12,
                            cornerRadius: 8,
                            callbacks: {
                                label: function (context) {
                                    let label = context.dataset.label || '';
                                    if (label) {
                                        label += ': ';
                                    }
                                    if (context.dataset.yAxisID === 'yRev') {
                                        label += new Intl.NumberFormat('vi-VN').format(context.parsed.y) + ' đ';
                                    } else {
                                        label += context.parsed.y + ' đơn';
                                    }
                                    return label;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                display: false
                            },
                            ticks: {
                                color: '#64748b',
                                font: { size: 12 }
                            }
                        },
                        yRev: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            grid: {
                                color: '#f1f5f9'
                            },
                            ticks: {
                                color: '#64748b',
                                font: { size: 11 },
                                callback: function (val) {
                                    if (val >= 1000000) return (val / 1000000).toFixed(1) + 'M';
                                    if (val >= 1000) return (val / 1000).toFixed(0) + 'k';
                                    return val;
                                }
                            }
                        },
                        yOrders: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            grid: {
                                drawOnChartArea: false
                            },
                            ticks: {
                                color: '#10b981',
                                font: { size: 11 },
                                precision: 0
                            }
                        }
                    }
                }
            });
        }

        // --- Chart 2: Order Status Distribution (Doughnut) ---
        const statusCanvas = document.getElementById('adminStatusChart');
        if (statusCanvas && dataPayload.statusLabels && dataPayload.statusLabels.length > 0) {
            const ctxStatus = statusCanvas.getContext('2d');

            // Generate harmonious semantic colors
            const colorMap = {
                'ĐÃ GIAO THÀNH CÔNG': '#10b981',
                'ĐANG VẬN CHUYỂN': '#2563eb',
                'CHỜ TÀI XẾ': '#f59e0b',
                'ĐANG PHÂN LOẠI': '#8b5cf6',
                'HỦY': '#ef4444',
                'ĐÃ HỦY': '#ef4444'
            };

            const bgColors = dataPayload.statusLabels.map(label => colorMap[label] || '#64748b');

            new Chart(ctxStatus, {
                type: 'doughnut',
                data: {
                    labels: dataPayload.statusLabels,
                    datasets: [
                        {
                            data: dataPayload.statusCounts,
                            backgroundColor: bgColors,
                            borderWidth: 2,
                            borderColor: '#ffffff',
                            hoverOffset: 6
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '72%',
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                boxWidth: 10,
                                usePointStyle: true,
                                padding: 14,
                                font: {
                                    family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                                    size: 11.5,
                                    weight: '600'
                                },
                                color: '#475569'
                            }
                        },
                        tooltip: {
                            backgroundColor: '#0f172a',
                            titleColor: '#ffffff',
                            bodyColor: '#e2e8f0',
                            padding: 10,
                            cornerRadius: 8,
                            callbacks: {
                                label: function (context) {
                                    const val = context.parsed;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const pct = total > 0 ? Math.round((val / total) * 100) : 0;
                                    return ` ${context.label}: ${val} đơn (${pct}%)`;
                                }
                            }
                        }
                    }
                }
            });
        }
    }

    /**
     * 3. CLIENT-SIDE LIVE TABLE SEARCH
     */
    function initLiveTableFilter() {
        const searchInput = document.getElementById('adminOrderSearchInput');
        const table = document.getElementById('adminRecentOrdersTable');

        if (!searchInput || !table) return;

        searchInput.addEventListener('input', function (e) {
            const query = e.target.value.toLowerCase().trim();
            const rows = table.querySelectorAll('tbody tr');

            rows.forEach(function (row) {
                // If it's the empty state row, skip
                if (row.classList.contains('empty-row')) return;

                const text = row.textContent.toLowerCase();
                if (text.includes(query)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }

})();
