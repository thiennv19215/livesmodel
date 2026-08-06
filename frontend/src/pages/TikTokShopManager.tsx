import React, { useState } from 'react';
import { ShoppingBag, Play, Pause, RefreshCw, Layers } from 'lucide-react';

export const TikTokShopManager: React.FC = () => {
  const [cdpPort, setCdpPort] = useState('9222');
  const [isConnected, setIsConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [scheduleActive, setScheduleActive] = useState(false);
  const [pinInterval, setPinInterval] = useState(60);

  const mockShopProducts = [
    { id: 'prod_001', name: 'Áo Thun Unisex Premium Cotton 100%', price: '199.000đ', status: 'Ghim lượt 1' },
    { id: 'prod_002', name: 'Quần Jean Nam Dáng Vừa Hàn Quốc', price: '349.000đ', status: 'Sẵn sàng' },
    { id: 'prod_003', name: 'Áo Khoác Du Dù Chống Nước', price: '289.000đ', status: 'Sẵn sàng' },
  ];

  const handleConnectBrowser = async () => {
    setLoading(true);
    setTimeout(() => {
      setIsConnected(true);
      setLoading(false);
    }, 1500);
  };

  const handleToggleSchedule = () => {
    setScheduleActive(!scheduleActive);
  };

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div className="glass-panel" style={{ padding: '32px' }}>
        <h2 style={{ fontSize: '22px', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
          <ShoppingBag size={24} color="var(--accent-purple)" /> Quản Lý Ghim Sản Phẩm TikTok Shop
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '24px' }}>
          Tự động kết nối trình duyệt Chrome/Edge (Playwright CDP) để cào danh sách và lập lịch ghim sản phẩm tuần tự trên phòng livestream.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
          <div className="glass-card" style={{ padding: '20px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: '12px' }}>Kết Nối Trình Duyệt CDP</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '4px', display: 'block' }}>Cổng Chrome Remote Debugging (CDP)</label>
                <input type="text" className="input-field" value={cdpPort} onChange={e => setCdpPort(e.target.value)} />
              </div>
              <button onClick={handleConnectBrowser} className="btn-primary" disabled={loading}>
                {loading ? <RefreshCw size={16} className="animate-spin" /> : <Layers size={16} />}
                {isConnected ? 'Đã Kết Nối Chrome CDP' : 'Kết Nối Trình Duyệt'}
              </button>
            </div>
          </div>

          <div className="glass-card" style={{ padding: '20px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: '12px' }}>Lập Lịch Ghim Tuần Tự</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '4px', display: 'block' }}>Thời gian ghim mỗi sản phẩm (Giây)</label>
                <input type="number" className="input-field" value={pinInterval} onChange={e => setPinInterval(Number(e.target.value))} />
              </div>
              <button onClick={handleToggleSchedule} className={scheduleActive ? "btn-secondary" : "btn-primary"} style={{ backgroundColor: scheduleActive ? 'rgba(239,68,68,0.2)' : undefined, color: scheduleActive ? '#ef4444' : undefined }}>
                {scheduleActive ? <Pause size={16} /> : <Play size={16} />}
                {scheduleActive ? 'Tạm Dừng Lịch Ghim' : 'Bắt Đầu Ghim Tự Động'}
              </button>
            </div>
          </div>
        </div>

        {/* Product Table */}
        <h3 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '12px' }}>Danh Sách Sản Phẩm TikTok Shop</h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                <th style={{ padding: '12px' }}>Mã sản phẩm</th>
                <th style={{ padding: '12px' }}>Tên sản phẩm</th>
                <th style={{ padding: '12px' }}>Giá bán</th>
                <th style={{ padding: '12px' }}>Trạng thái ghim</th>
                <th style={{ padding: '12px' }}>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {mockShopProducts.map(p => (
                <tr key={p.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '12px', color: 'var(--accent-cyan)' }}>{p.id}</td>
                  <td style={{ padding: '12px', fontWeight: '500' }}>{p.name}</td>
                  <td style={{ padding: '12px', color: 'var(--accent-pink)' }}>{p.price}</td>
                  <td style={{ padding: '12px' }}>
                    <span style={{ backgroundColor: 'rgba(139,92,246,0.15)', color: 'var(--accent-purple)', padding: '2px 8px', borderRadius: '6px', fontSize: '12px' }}>
                      {p.status}
                    </span>
                  </td>
                  <td style={{ padding: '12px' }}>
                    <button className="btn-secondary" style={{ padding: '6px 12px', fontSize: '12px' }}>Ghim Ngay</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
