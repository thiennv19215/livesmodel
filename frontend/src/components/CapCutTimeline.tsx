import React from 'react';
import { Play, Square, Volume2, User, MessageSquare, Music, Film } from 'lucide-react';
import type { SceneElement } from './CapCutCanvas';

interface CapCutTimelineProps {
  selectedElement: SceneElement | null;
  onSelectElement: (element: SceneElement) => void;
  isPlaying: boolean;
  onPlayTest: () => void;
  hasVideo?: boolean;
}

export const CapCutTimeline: React.FC<CapCutTimelineProps> = ({
  selectedElement,
  onSelectElement,
  isPlaying,
  onPlayTest,
  hasVideo = false,
}) => {
  return (
    <div
      style={{
        height: '180px',
        background: '#090d16',
        borderRadius: '16px',
        border: '1px solid var(--border-color)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Timeline Controls Header */}
      <div
        style={{
          height: '42px',
          background: 'rgba(15, 23, 42, 0.95)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 20px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={onPlayTest}
            className="btn-primary"
            style={{ padding: '4px 12px', fontSize: '12px' }}
          >
            {isPlaying ? <Square size={14} /> : <Play size={14} />}
            {isPlaying ? 'Dừng Xem Thử' : 'Phát Thử (Play)'}
          </button>
          <span style={{ fontFamily: 'monospace', fontSize: '13px', color: 'var(--accent-cyan)', fontWeight: 'bold' }}>
            00:00:0{isPlaying ? '2' : '0'}.15 / 00:00:05.00
          </span>
        </div>

        {/* Dynamic Audio VU Meter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Volume2 size={16} color={isPlaying ? 'var(--accent-cyan)' : 'var(--text-secondary)'} />
          <div style={{ display: 'flex', gap: '3px', alignItems: 'flex-end', height: '16px' }}>
            {[40, 75, 100, 60, 90, 50, 80, 30].map((h, idx) => (
              <div
                key={idx}
                style={{
                  width: '4px',
                  height: isPlaying ? `${h}%` : '4px',
                  background: h > 80 ? '#ec4899' : 'var(--accent-cyan)',
                  borderRadius: '2px',
                  transition: 'height 0.15s ease',
                }}
              />
            ))}
          </div>
        </div>
      </div>

      {/* CapCut Track Stack */}
      <div style={{ flex: 1, padding: '10px 16px', display: 'flex', flexDirection: 'column', gap: '8px', overflowY: 'auto' }}>
        {hasVideo && (
          <div
            onClick={() => onSelectElement('video')}
            style={{
              height: '34px',
              display: 'flex',
              alignItems: 'center',
              background: selectedElement === 'video' ? 'rgba(249, 115, 22, 0.2)' : 'rgba(15, 23, 42, 0.6)',
              border: selectedElement === 'video' ? '1px solid #fb923c' : '1px solid transparent',
              borderRadius: '8px',
              padding: '0 12px',
              cursor: 'pointer',
            }}
          >
            <div style={{ width: '130px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', fontWeight: 600, color: '#fb923c' }}>
              <Film size={14} /> Video nguồn
            </div>
            <div style={{ flex: 1, height: '18px', background: 'rgba(249, 115, 22, 0.28)', borderRadius: '4px', display: 'flex', alignItems: 'center', padding: '0 10px', fontSize: '10px', color: '#fff' }}>
              Layer video độc lập · kéo, đổi kích thước và xoay
            </div>
          </div>
        )}

        {/* Track 1: Avatar Track */}
        <div
          onClick={() => onSelectElement('avatar')}
          style={{
            height: '34px',
            display: 'flex',
            alignItems: 'center',
            background: selectedElement === 'avatar' ? 'rgba(139, 92, 246, 0.2)' : 'rgba(15, 23, 42, 0.6)',
            border: selectedElement === 'avatar' ? '1px solid var(--accent-purple)' : '1px solid transparent',
            borderRadius: '8px',
            padding: '0 12px',
            cursor: 'pointer',
          }}
        >
          <div style={{ width: '130px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', fontWeight: 600, color: 'var(--accent-purple)' }}>
            <User size={14} /> Track 1: MC Avatar
          </div>
          <div style={{ flex: 1, height: '18px', background: 'rgba(139, 92, 246, 0.3)', borderRadius: '4px', display: 'flex', alignItems: 'center', padding: '0 10px', fontSize: '10px', color: '#fff' }}>
            Layer MC Avatar AI (Xoay & Thu phóng)
          </div>
        </div>

        {/* Track 2: Subtitle Track */}
        <div
          onClick={() => onSelectElement('caption')}
          style={{
            height: '34px',
            display: 'flex',
            alignItems: 'center',
            background: selectedElement === 'caption' ? 'rgba(6, 182, 212, 0.2)' : 'rgba(15, 23, 42, 0.6)',
            border: selectedElement === 'caption' ? '1px solid var(--accent-cyan)' : '1px solid transparent',
            borderRadius: '8px',
            padding: '0 12px',
            cursor: 'pointer',
          }}
        >
          <div style={{ width: '130px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', fontWeight: 600, color: 'var(--accent-cyan)' }}>
            <MessageSquare size={14} /> Track 2: Phụ Đề
          </div>
          <div style={{ flex: 1, height: '18px', background: 'rgba(6, 182, 212, 0.3)', borderRadius: '4px', display: 'flex', alignItems: 'center', padding: '0 10px', fontSize: '10px', color: '#fff' }}>
            CapCut Subtitle Dynamic Caption Layer
          </div>
        </div>

        {/* Track 3: Audio Stream Track */}
        <div
          style={{
            height: '34px',
            display: 'flex',
            alignItems: 'center',
            background: 'rgba(15, 23, 42, 0.4)',
            borderRadius: '8px',
            padding: '0 12px',
          }}
        >
          <div style={{ width: '130px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>
            <Music size={14} /> Track 3: Audio TTS
          </div>
          <div style={{ flex: 1, height: '18px', background: isPlaying ? 'rgba(236, 72, 153, 0.3)' : 'rgba(255, 255, 255, 0.05)', borderRadius: '4px', display: 'flex', alignItems: 'center', padding: '0 10px', fontSize: '10px', color: '#cbd5e1' }}>
            {isPlaying ? '🔊 Sóng Âm Giọng Đọc TTS Đang Phát...' : 'Audio Stream Output Channel'}
          </div>
        </div>
      </div>
    </div>
  );
};
