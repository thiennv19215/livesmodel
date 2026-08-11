import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Radio, Video, Package, Cpu, Volume2, Camera, ShoppingBag, Activity } from 'lucide-react';
const LiveConsole = lazy(() => import('./pages/LiveConsole').then(module => ({ default: module.LiveConsole })));
const TikTokConnection = lazy(() => import('./pages/TikTokConnection').then(module => ({ default: module.TikTokConnection })));
const ProductManager = lazy(() => import('./pages/ProductManager').then(module => ({ default: module.ProductManager })));
const AISettings = lazy(() => import('./pages/AISettings').then(module => ({ default: module.AISettings })));
const TTSSettings = lazy(() => import('./pages/TTSSettings').then(module => ({ default: module.TTSSettings })));
const AvatarStudio = lazy(() => import('./pages/AvatarStudio').then(module => ({ default: module.AvatarStudio })));
const TikTokShopManager = lazy(() => import('./pages/TikTokShopManager').then(module => ({ default: module.TikTokShopManager })));

const NavItem: React.FC<{ to: string; label: string; icon: React.ReactNode }> = ({ to, label, icon }) => {
  const location = useLocation();
  const isActive = location.pathname === to;
  return (
    <Link
      to={to}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        padding: '12px 18px',
        borderRadius: '12px',
        color: isActive ? '#ffffff' : 'var(--text-secondary)',
        backgroundColor: isActive ? 'rgba(139, 92, 246, 0.2)' : 'transparent',
        borderLeft: isActive ? '4px solid var(--accent-purple)' : '4px solid transparent',
        textDecoration: 'none',
        fontWeight: isActive ? '600' : 'normal',
        transition: 'all 0.2s ease'
      }}
    >
      {icon}
      <span>{label}</span>
    </Link>
  );
};

export function App() {
  return (
    <BrowserRouter>
      <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'var(--bg-primary)' }}>
        {/* Sidebar */}
        <aside style={{
          width: '260px',
          backgroundColor: 'var(--bg-surface)',
          borderRight: '1px solid var(--border-color)',
          display: 'flex',
          flexDirection: 'column',
          padding: '24px 16px',
          gap: '24px'
        }}>
          {/* App Branding */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', paddingLeft: '8px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #8b5cf6, #ec4899)',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              boxShadow: '0 4px 12px rgba(139, 92, 246, 0.4)'
            }}>
              <Radio size={22} color="white" />
            </div>
            <div>
              <h1 style={{ fontSize: '18px', fontWeight: 'bold', color: 'white', lineHeight: '1.2' }}>LiveAgent AI</h1>
              <span style={{ fontSize: '12px', color: 'var(--accent-cyan)' }}>Python & React Edition</span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <NavItem to="/" label="Live Console" icon={<Activity size={20} />} />
            <NavItem to="/tiktok" label="Kết Nối TikTok" icon={<Video size={20} />} />
            <NavItem to="/products" label="Sản Phẩm & Script" icon={<Package size={20} />} />
            <NavItem to="/shop" label="TikTok Shop Auto" icon={<ShoppingBag size={20} />} />
            <NavItem to="/avatar" label="Avatar Studio" icon={<Camera size={20} />} />
            <NavItem to="/ai" label="AI Provider" icon={<Cpu size={20} />} />
            <NavItem to="/tts" label="Giọng Đọc TTS" icon={<Volume2 size={20} />} />
          </nav>
        </aside>

        {/* Main Content Area */}
        <main style={{ flex: 1, padding: '32px', overflowY: 'auto' }}>
          <Suspense fallback={<div style={{ color: 'var(--text-secondary)' }}>Đang tải màn hình…</div>}>
            <Routes>
              <Route path="/" element={<LiveConsole />} />
              <Route path="/tiktok" element={<TikTokConnection />} />
              <Route path="/products" element={<ProductManager />} />
              <Route path="/shop" element={<TikTokShopManager />} />
              <Route path="/avatar" element={<AvatarStudio />} />
              <Route path="/ai" element={<AISettings />} />
              <Route path="/tts" element={<TTSSettings />} />
            </Routes>
          </Suspense>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
