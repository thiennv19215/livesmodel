import React from 'react';
import { AlertTriangle, ShoppingBag } from 'lucide-react';

export const TikTokShopManager: React.FC = () => (
  <div style={{ maxWidth: '900px', margin: '0 auto' }}>
    <div className="glass-panel" style={{ padding: '32px' }}>
      <h2 style={{ fontSize: '22px', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
        <ShoppingBag size={24} color="var(--accent-purple)" /> Quản Lý Ghim Sản Phẩm TikTok Shop
      </h2>
      <div style={{ marginTop: '24px', padding: '20px', borderRadius: '12px', border: '1px solid rgba(245, 158, 11, 0.4)', background: 'rgba(245, 158, 11, 0.08)', display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
        <AlertTriangle size={24} color="#f59e0b" />
        <div>
          <h3 style={{ margin: '0 0 8px', fontSize: '16px' }}>Tính năng đang được phát triển</h3>
          <p style={{ margin: 0, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            Kết nối Chrome CDP, đồng bộ danh sách TikTok Shop và lịch ghim sản phẩm chưa được tích hợp với backend.
            Giao diện mô phỏng trước đây đã được tắt để tránh báo trạng thái thành công sai.
          </p>
        </div>
      </div>
    </div>
  </div>
);
