import React, { useState } from 'react';
import {
  MoveHorizontal,
  MoveVertical,
  ArrowUp,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  Sliders,
  User,
  Type,
  Palette,
  Volume2,
  Upload,
  Film,
  LoaderCircle,
  AlertCircle,
  CheckCircle2,
  RotateCcw,
} from 'lucide-react';
import type { SceneConfig, SceneElement } from './CapCutCanvas';

interface CapCutInspectorProps {
  config: SceneConfig;
  onChangeConfig: (newConfig: Partial<SceneConfig>) => void;
  selectedElement: SceneElement | null;
  onSelectElement: (element: SceneElement) => void;
  onTestSpeech?: () => void;
  onUploadAvatar?: (file: File) => void;
  isUploadingAvatar?: boolean;
  avatarUploadError?: string | null;
  avatarUploadSuccess?: boolean;
}

export const CapCutInspector: React.FC<CapCutInspectorProps> = ({
  config,
  onChangeConfig,
  selectedElement,
  onSelectElement,
  onTestSpeech,
  onUploadAvatar,
  isUploadingAvatar = false,
  avatarUploadError,
  avatarUploadSuccess = false,
}) => {
  const [activeTab, setActiveTab] = useState<'transform' | 'avatar' | 'subtitle' | 'canvas'>('transform');

  const currentElement = selectedElement || 'avatar';

  const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

  const updatePosition = (axis: 'x' | 'y', value: number) => {
    if (currentElement === 'video') {
      onChangeConfig(axis === 'x' ? { video_x: value } : { video_y: value });
    } else if (currentElement === 'avatar') {
      onChangeConfig(axis === 'x' ? { avatar_x: value } : { avatar_y: value });
    } else {
      onChangeConfig(axis === 'x' ? { caption_x: value } : { caption_y: value });
    }
  };

  const currentX = currentElement === 'video'
    ? config.video_x
    : currentElement === 'avatar'
      ? config.avatar_x
      : config.caption_x;
  const currentY = currentElement === 'video'
    ? config.video_y
    : currentElement === 'avatar'
      ? config.avatar_y
      : config.caption_y;

  const alignHorizontalCenter = () => {
    updatePosition('x', 50);
  };

  const alignVerticalCenter = () => {
    updatePosition('y', 50);
  };

  const alignTop = () => {
    if (currentElement === 'video') updatePosition('y', clamp(config.video_height / 2, 0, 50));
    else if (currentElement === 'avatar') updatePosition('y', 25);
    else updatePosition('y', 15);
  };

  const alignBottom = () => {
    if (currentElement === 'video') updatePosition('y', clamp(100 - config.video_height / 2, 50, 100));
    else if (currentElement === 'avatar') updatePosition('y', 75);
    else updatePosition('y', 88);
  };

  const alignLeft = () => {
    if (currentElement === 'video') updatePosition('x', clamp(config.video_width / 2, 0, 50));
    else updatePosition('x', 25);
  };

  const alignRight = () => {
    if (currentElement === 'video') updatePosition('x', clamp(100 - config.video_width / 2, 50, 100));
    else updatePosition('x', 75);
  };

  const resetSelectedTransform = () => {
    if (currentElement === 'video') {
      onChangeConfig({ video_x: 50, video_y: 50, video_width: 100, video_height: 100, video_rotation: 0 });
    } else if (currentElement === 'avatar') {
      onChangeConfig({ avatar_x: 50, avatar_y: 65, avatar_scale: 100 });
    } else {
      onChangeConfig({ caption_x: 50, caption_y: 88 });
    }
  };

  return (
    <div
      style={{
        width: '340px',
        background: '#0e1526',
        borderRadius: '16px',
        border: '1px solid var(--border-color)',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      {/* CapCut Inspector Tab Header */}
      <div
        style={{
          display: 'flex',
          background: 'rgba(15, 23, 42, 0.95)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        }}
      >
        <button
          onClick={() => setActiveTab('transform')}
          style={{
            flex: 1,
            padding: '12px 4px',
            fontSize: '12px',
            fontWeight: 600,
            background: activeTab === 'transform' ? 'rgba(139, 92, 246, 0.15)' : 'transparent',
            color: activeTab === 'transform' ? 'var(--accent-purple)' : 'var(--text-secondary)',
            border: 'none',
            borderBottom: activeTab === 'transform' ? '2px solid var(--accent-purple)' : 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '4px',
          }}
        >
          <Sliders size={14} /> Căn Chỉnh
        </button>
        <button
          onClick={() => setActiveTab('avatar')}
          style={{
            flex: 1,
            padding: '12px 4px',
            fontSize: '12px',
            fontWeight: 600,
            background: activeTab === 'avatar' ? 'rgba(139, 92, 246, 0.15)' : 'transparent',
            color: activeTab === 'avatar' ? 'var(--accent-purple)' : 'var(--text-secondary)',
            border: 'none',
            borderBottom: activeTab === 'avatar' ? '2px solid var(--accent-purple)' : 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '4px',
          }}
        >
          <User size={14} /> MC Avatar
        </button>
        <button
          onClick={() => setActiveTab('subtitle')}
          style={{
            flex: 1,
            padding: '12px 4px',
            fontSize: '12px',
            fontWeight: 600,
            background: activeTab === 'subtitle' ? 'rgba(139, 92, 246, 0.15)' : 'transparent',
            color: activeTab === 'subtitle' ? 'var(--accent-purple)' : 'var(--text-secondary)',
            border: 'none',
            borderBottom: activeTab === 'subtitle' ? '2px solid var(--accent-purple)' : 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '4px',
          }}
        >
          <Type size={14} /> Phụ Đề
        </button>
        <button
          onClick={() => setActiveTab('canvas')}
          style={{
            flex: 1,
            padding: '12px 4px',
            fontSize: '12px',
            fontWeight: 600,
            background: activeTab === 'canvas' ? 'rgba(139, 92, 246, 0.15)' : 'transparent',
            color: activeTab === 'canvas' ? 'var(--accent-purple)' : 'var(--text-secondary)',
            border: 'none',
            borderBottom: activeTab === 'canvas' ? '2px solid var(--accent-purple)' : 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '4px',
          }}
        >
          <Palette size={14} /> Phông Nền
        </button>
      </div>

      {/* Tab Content Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Tab 1: Transform & Alignment */}
        {activeTab === 'transform' && (
          <>
            {/* Target Element Switcher */}
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '4px', borderRadius: '10px', display: 'flex', border: '1px solid var(--border-color)' }}>
              <button
                onClick={() => onSelectElement('video')}
                disabled={!config.video_media_url}
                style={{
                  flex: 1,
                  padding: '8px 4px',
                  borderRadius: '8px',
                  border: 'none',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: config.video_media_url ? 'pointer' : 'not-allowed',
                  background: currentElement === 'video' ? '#0891b2' : 'transparent',
                  color: config.video_media_url ? '#fff' : '#64748b',
                }}
              >
                Video nguồn
              </button>
              <button
                onClick={() => onSelectElement('avatar')}
                style={{
                  flex: 1,
                  padding: '8px',
                  borderRadius: '8px',
                  border: 'none',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  background: currentElement === 'avatar' ? 'var(--accent-purple)' : 'transparent',
                  color: '#fff',
                }}
              >
                🎭 MC Avatar
              </button>
              <button
                onClick={() => onSelectElement('caption')}
                style={{
                  flex: 1,
                  padding: '8px',
                  borderRadius: '8px',
                  border: 'none',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  background: currentElement === 'caption' ? 'var(--accent-cyan)' : 'transparent',
                  color: '#fff',
                }}
              >
                💬 Khung Phụ Đề
              </button>
            </div>

            {/* Quick Alignment Actions */}
            <div>
              <label style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '10px', display: 'block' }}>
                Căn vị trí nhanh (Quick Alignment):
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
                <button onClick={alignLeft} className="btn-secondary" style={{ padding: '8px', justifyContent: 'center', fontSize: '11px' }}>
                  <ArrowLeft size={14} /> Trái
                </button>
                <button onClick={alignHorizontalCenter} className="btn-secondary" style={{ padding: '8px', justifyContent: 'center', fontSize: '11px', color: 'var(--accent-cyan)' }}>
                  <MoveHorizontal size={14} /> Giữa Ngang
                </button>
                <button onClick={alignRight} className="btn-secondary" style={{ padding: '8px', justifyContent: 'center', fontSize: '11px' }}>
                  <ArrowRight size={14} /> Phải
                </button>
                <button onClick={alignTop} className="btn-secondary" style={{ padding: '8px', justifyContent: 'center', fontSize: '11px' }}>
                  <ArrowUp size={14} /> Trên Top
                </button>
                <button onClick={alignVerticalCenter} className="btn-secondary" style={{ padding: '8px', justifyContent: 'center', fontSize: '11px', color: 'var(--accent-purple)' }}>
                  <MoveVertical size={14} /> Giữa Dọc
                </button>
                <button onClick={alignBottom} className="btn-secondary" style={{ padding: '8px', justifyContent: 'center', fontSize: '11px' }}>
                  <ArrowDown size={14} /> Phía Dưới
                </button>
              </div>
            </div>

            {/* Precise Coordinates Inputs */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '6px' }}>
                  <span>Tọa độ Ngang (X%):</span>
                  <span style={{ fontWeight: 'bold', color: 'var(--accent-cyan)' }}>
                    {currentX}%
                  </span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={currentX}
                  onChange={(e) => updatePosition('x', Number(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--accent-cyan)' }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '6px' }}>
                  <span>Tọa độ Dọc (Y%):</span>
                  <span style={{ fontWeight: 'bold', color: 'var(--accent-purple)' }}>
                    {currentY}%
                  </span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={currentY}
                  onChange={(e) => updatePosition('y', Number(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--accent-purple)' }}
                />
              </div>

              {currentElement === 'avatar' && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '6px' }}>
                    <span>Kích thước Scale MC (%):</span>
                    <span style={{ fontWeight: 'bold', color: '#f59e0b' }}>{config.avatar_scale || 100}%</span>
                  </div>
                  <input
                    type="range"
                    min={50}
                    max={200}
                    value={config.avatar_scale || 100}
                    onChange={(e) => onChangeConfig({ avatar_scale: Number(e.target.value) })}
                    style={{ width: '100%', accentColor: '#f59e0b' }}
                  />
                </div>
              )}

              {currentElement === 'video' && (
                <>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '6px' }}>
                      <span>Chiều rộng khung:</span>
                      <span style={{ fontWeight: 'bold', color: '#22d3ee' }}>{config.video_width}%</span>
                    </div>
                    <input
                      type="range"
                      min={10}
                      max={200}
                      value={config.video_width}
                      onChange={(event) => onChangeConfig({ video_width: Number(event.target.value) })}
                      style={{ width: '100%', accentColor: '#22d3ee' }}
                    />
                  </div>

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '6px' }}>
                      <span>Chiều cao khung:</span>
                      <span style={{ fontWeight: 'bold', color: '#38bdf8' }}>{config.video_height}%</span>
                    </div>
                    <input
                      type="range"
                      min={10}
                      max={200}
                      value={config.video_height}
                      onChange={(event) => onChangeConfig({ video_height: Number(event.target.value) })}
                      style={{ width: '100%', accentColor: '#38bdf8' }}
                    />
                  </div>

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '6px' }}>
                      <span>Góc xoay:</span>
                      <span style={{ fontWeight: 'bold', color: '#f59e0b' }}>{config.video_rotation}°</span>
                    </div>
                    <input
                      type="range"
                      min={-180}
                      max={180}
                      value={config.video_rotation}
                      onChange={(event) => onChangeConfig({ video_rotation: Number(event.target.value) })}
                      style={{ width: '100%', accentColor: '#f59e0b' }}
                    />
                  </div>

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '6px' }}>
                      <span>Hiển thị trong khung</span>
                      <span style={{ color: 'var(--accent-cyan)' }}>{config.video_fit === 'cover' ? 'Lấp đầy' : 'Toàn bộ'}</span>
                    </div>
                    <select
                      value={config.video_fit || 'contain'}
                      onChange={(event) => onChangeConfig({ video_fit: event.target.value as 'contain' | 'cover' })}
                      style={{ width: '100%', background: 'rgba(30, 41, 59, 0.8)', color: '#fff', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '8px 10px' }}
                    >
                      <option value="contain">Toàn bộ video (contain)</option>
                      <option value="cover">Lấp đầy khung (cover)</option>
                    </select>
                  </div>
                </>
              )}
            </div>

            <button type="button" onClick={resetSelectedTransform} className="btn-secondary" style={{ width: '100%', justifyContent: 'center', fontSize: '12px' }}>
              <RotateCcw size={14} /> Đặt lại vị trí và kích thước
            </button>
          </>
        )}

        {/* Tab 2: Avatar Settings */}
        {activeTab === 'avatar' && (
          <>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <label style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)' }}>
                Nguồn hình MC
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <button
                  type="button"
                  onClick={() => onChangeConfig({ avatar_mode: 'builtin' })}
                  className={config.avatar_mode !== 'video' ? 'btn-primary' : 'btn-secondary'}
                  style={{ justifyContent: 'center', fontSize: '12px' }}
                >
                  <User size={15} /> Avatar mặc định
                </button>
                <button
                  type="button"
                  onClick={() => config.avatar_media_url && onChangeConfig({ avatar_mode: 'video' })}
                  className={config.avatar_mode === 'video' ? 'btn-primary' : 'btn-secondary'}
                  disabled={!config.avatar_media_url}
                  style={{ justifyContent: 'center', fontSize: '12px' }}
                >
                  <Film size={15} /> Video AI
                </button>
              </div>

              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  padding: '11px',
                  borderRadius: '10px',
                  border: '1px dashed var(--accent-cyan)',
                  color: '#67e8f9',
                  cursor: isUploadingAvatar ? 'wait' : 'pointer',
                  fontSize: '12px',
                  fontWeight: 600,
                }}
              >
                {isUploadingAvatar ? <LoaderCircle size={16} className="animate-spin" /> : <Upload size={16} />}
                {isUploadingAvatar ? 'Đang tải video...' : 'Tải video MP4/WebM (tối đa 50 MB)'}
                <input
                  type="file"
                  accept="video/mp4,video/webm,.mp4,.webm"
                  disabled={isUploadingAvatar}
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) onUploadAvatar?.(file);
                    event.currentTarget.value = '';
                  }}
                  style={{ display: 'none' }}
                />
              </label>

              <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                Video sẽ tự lặp và luôn tắt tiếng. Hãy dùng video bạn có quyền sử dụng; giọng TTS được phát riêng và không nhép miệng.
              </div>

              {avatarUploadError && (
                <div style={{ display: 'flex', gap: '7px', color: '#fca5a5', fontSize: '11px' }}>
                  <AlertCircle size={14} /> {avatarUploadError}
                </div>
              )}
              {avatarUploadSuccess && (
                <div style={{ display: 'flex', gap: '7px', color: '#86efac', fontSize: '11px' }}>
                  <CheckCircle2 size={14} /> Đã tải video. Bấm “Lưu Vị Trí & Cấu Hình” để cập nhật OBS.
                </div>
              )}

              {config.avatar_mode === 'video' && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '6px' }}>
                    <span>Hiển thị video</span>
                    <span style={{ color: 'var(--accent-cyan)' }}>{config.avatar_fit === 'cover' ? 'Lấp đầy' : 'Toàn bộ'}</span>
                  </div>
                  <select
                    value={config.avatar_fit || 'contain'}
                    onChange={(event) => onChangeConfig({ avatar_fit: event.target.value as 'contain' | 'cover' })}
                    style={{ width: '100%', background: 'rgba(30, 41, 59, 0.8)', color: '#fff', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '8px 10px' }}
                  >
                    <option value="contain">Toàn bộ video (contain)</option>
                    <option value="cover">Lấp đầy khung (cover)</option>
                  </select>
                </div>
              )}
            </div>

            <div>
              <label style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px', display: 'block' }}>
                Chọn Mẫu MC Avatar AI:
              </label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {[
                  { id: 'default', title: '🎭 MC Virtual Host 2D (Default)', desc: 'Phong cách hoạt hình hiện đại' },
                  { id: 'anime', title: '🌸 Anime Host Female', desc: 'Mẫu MC Anime Nhật Bản' },
                  { id: 'corporate', title: '💼 Business MC Male', desc: 'MC vest công sở thanh lịch' },
                  { id: 'cyberpunk', title: '⚡ Cyberpunk Streamer', desc: 'Phong cách độc lạ nổi bật' },
                ].map((item) => (
                  <div
                    key={item.id}
                    onClick={() => onChangeConfig({ avatar_style: item.id })}
                    style={{
                      padding: '12px',
                      borderRadius: '10px',
                      border: config.avatar_style === item.id ? '2px solid var(--accent-purple)' : '1px solid var(--border-color)',
                      background: config.avatar_style === item.id ? 'rgba(139, 92, 246, 0.15)' : 'rgba(15, 23, 42, 0.6)',
                      cursor: 'pointer',
                    }}
                  >
                    <div style={{ fontSize: '13px', fontWeight: 'bold' }}>{item.title}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>{item.desc}</div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <button
                onClick={onTestSpeech}
                className="btn-primary"
                style={{ width: '100%', justifyContent: 'center', marginTop: '10px' }}
              >
                <Volume2 size={16} /> Thử Giọng Nói MC (Test Animation)
              </button>
            </div>
          </>
        )}

        {/* Tab 3: Subtitle Styling */}
        {activeTab === 'subtitle' && (
          <>
            <div>
              <label style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px', display: 'block' }}>
                Bộ Preset Mẫu Phụ Đề CapCut:
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                {[
                  { id: 'capcut_yellow', title: '🟡 CapCut Vàng', color: '#FACC15' },
                  { id: 'cyberpunk', title: '🟣 Neon Cyber', color: '#EC4899' },
                  { id: 'minimal_dark', title: '⚪ Minimal Dark', color: '#F8FAFC' },
                  { id: 'default', title: '🔵 Purple Glass', color: '#A78BFA' },
                ].map((preset) => (
                  <button
                    key={preset.id}
                    onClick={() => onChangeConfig({ caption_preset: preset.id })}
                    style={{
                      padding: '10px',
                      borderRadius: '8px',
                      border: config.caption_preset === preset.id ? `2px solid ${preset.color}` : '1px solid var(--border-color)',
                      background: 'rgba(15, 23, 42, 0.8)',
                      color: preset.color,
                      fontWeight: 'bold',
                      fontSize: '12px',
                      cursor: 'pointer',
                    }}
                  >
                    {preset.title}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '6px' }}>
                <span>Cỡ chữ Phụ đề:</span>
                <span style={{ fontWeight: 'bold', color: 'var(--accent-purple)' }}>{config.caption_font_size || 18}px</span>
              </div>
              <input
                type="range"
                min={14}
                max={32}
                value={config.caption_font_size || 18}
                onChange={(e) => onChangeConfig({ caption_font_size: Number(e.target.value) })}
                style={{ width: '100%', accentColor: 'var(--accent-purple)' }}
              />
            </div>
          </>
        )}

        {/* Tab 4: Canvas Background Mode */}
        {activeTab === 'canvas' && (
          <>
            <div>
              <label style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px', display: 'block' }}>
                Chế độ Phông Nền OBS Overlay:
              </label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {[
                  { id: 'transparent', title: '🔳 Trong suốt (Transparent)', desc: 'Phù hợp đè lên Game/Camera trong OBS Studio' },
                  { id: 'chroma_green', title: '🟩 Phông Xanh (Chroma Key Green #00FF00)', desc: 'Để tách nền bằng bộ lọc Chroma Key OBS' },
                  { id: 'dark_studio', title: '⬛ Phông Tối Studio', desc: 'Phông nền xám tối cao cấp' },
                ].map((bg) => (
                  <div
                    key={bg.id}
                    onClick={() => onChangeConfig({ bg_mode: bg.id })}
                    style={{
                      padding: '12px',
                      borderRadius: '10px',
                      border: config.bg_mode === bg.id ? '2px solid var(--accent-cyan)' : '1px solid var(--border-color)',
                      background: config.bg_mode === bg.id ? 'rgba(6, 182, 212, 0.15)' : 'rgba(15, 23, 42, 0.6)',
                      cursor: 'pointer',
                    }}
                  >
                    <div style={{ fontSize: '13px', fontWeight: 'bold' }}>{bg.title}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>{bg.desc}</div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
