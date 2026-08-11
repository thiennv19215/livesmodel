import React, { useEffect, useRef, useState } from 'react';
import { Grid, Eye, EyeOff, Smartphone, Monitor, Square } from 'lucide-react';

export type SceneElement = 'video' | 'avatar' | 'caption';

export interface SceneConfig {
  aspect_ratio: string;
  video_media_url: string;
  video_name: string;
  video_x: number;
  video_y: number;
  video_width: number;
  video_height: number;
  video_rotation: number;
  video_fit: 'contain' | 'cover';
  video_visible: boolean;
  avatar_x: number;
  avatar_y: number;
  avatar_scale: number;
  avatar_style: string;
  avatar_mode: 'builtin' | 'video';
  avatar_media_url: string;
  avatar_fit: 'contain' | 'cover';
  avatar_visible: boolean;
  caption_x: number;
  caption_y: number;
  caption_font_size: number;
  caption_text_color: string;
  caption_bg_color: string;
  caption_preset: string;
  caption_visible: boolean;
  bg_mode: string;
}

interface CapCutCanvasProps {
  config: SceneConfig;
  onChangeConfig: (newConfig: Partial<SceneConfig>) => void;
  selectedElement: SceneElement | null;
  onSelectElement: (element: SceneElement | null) => void;
  isSpeakingTest?: boolean;
}

type InteractionMode = 'move' | 'resize' | 'rotate';

interface CanvasInteraction {
  mode: InteractionMode;
  element: SceneElement;
  startClientX: number;
  startClientY: number;
  startX: number;
  startY: number;
  startScale: number;
  startWidth: number;
  startHeight: number;
  startRotation: number;
  startDistance: number;
  startAngle: number;
}

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

const normalizeRotation = (degrees: number) => {
  let normalized = degrees % 360;
  if (normalized > 180) normalized -= 360;
  if (normalized < -180) normalized += 360;
  return Math.round(normalized);
};

const getAngle = (clientX: number, clientY: number, centerX: number, centerY: number) =>
  Math.atan2(clientY - centerY, clientX - centerX) * (180 / Math.PI);

export const CapCutCanvas: React.FC<CapCutCanvasProps> = ({
  config,
  onChangeConfig,
  selectedElement,
  onSelectElement,
  isSpeakingTest = false,
}) => {
  const canvasRef = useRef<HTMLDivElement>(null);
  const interactionRef = useRef<CanvasInteraction | null>(null);
  const onChangeConfigRef = useRef(onChangeConfig);
  const selectedElementRef = useRef(selectedElement);
  const configRef = useRef(config);
  const [interactionMode, setInteractionMode] = useState<InteractionMode | null>(null);
  const [activeElement, setActiveElement] = useState<SceneElement | null>(null);
  const [showGrid, setShowGrid] = useState(true);
  const [showTikTokOverlay, setShowTikTokOverlay] = useState(false);
  const [snapX, setSnapX] = useState(false);
  const [snapY, setSnapY] = useState(false);
  const [zoom, setZoom] = useState(100);

  useEffect(() => {
    onChangeConfigRef.current = onChangeConfig;
  }, [onChangeConfig]);

  useEffect(() => {
    selectedElementRef.current = selectedElement;
  }, [selectedElement]);

  useEffect(() => {
    configRef.current = config;
  }, [config]);

  const getAspectRatioStyle = () => {
    switch (config.aspect_ratio) {
      case '16:9':
        return { height: '100%', width: 'auto', maxHeight: '100%', maxWidth: '100%', aspectRatio: '16/9' };
      case '1:1':
        return { height: '100%', width: 'auto', maxHeight: '100%', maxWidth: '100%', aspectRatio: '1/1' };
      case '9:16':
      default:
        return { height: '100%', width: 'auto', maxHeight: '100%', maxWidth: '100%', aspectRatio: '9/16' };
    }
  };

  const getElementPosition = (element: SceneElement) => {
    if (element === 'video') return { x: config.video_x, y: config.video_y };
    if (element === 'avatar') return { x: config.avatar_x, y: config.avatar_y };
    return { x: config.caption_x, y: config.caption_y };
  };

  const beginInteraction = (
    event: React.PointerEvent,
    element: SceneElement,
    mode: InteractionMode,
  ) => {
    if (!canvasRef.current) return;
    event.preventDefault();
    event.stopPropagation();
    onSelectElement(element);

    const rect = canvasRef.current.getBoundingClientRect();
    const position = getElementPosition(element);
    const centerX = rect.left + (position.x / 100) * rect.width;
    const centerY = rect.top + (position.y / 100) * rect.height;
    const startDistance = Math.max(1, Math.hypot(event.clientX - centerX, event.clientY - centerY));

    interactionRef.current = {
      mode,
      element,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startX: position.x,
      startY: position.y,
      startScale: config.avatar_scale || 100,
      startWidth: config.video_width || 100,
      startHeight: config.video_height || 100,
      startRotation: config.video_rotation || 0,
      startDistance,
      startAngle: getAngle(event.clientX, event.clientY, centerX, centerY),
    };
    setInteractionMode(mode);
    setActiveElement(element);
  };

  useEffect(() => {
    const handlePointerMove = (event: PointerEvent) => {
      const interaction = interactionRef.current;
      const canvas = canvasRef.current;
      if (!interaction || !canvas) return;

      const rect = canvas.getBoundingClientRect();
      if (!rect.width || !rect.height) return;

      if (interaction.mode === 'move') {
        let newX = interaction.startX + ((event.clientX - interaction.startClientX) / rect.width) * 100;
        let newY = interaction.startY + ((event.clientY - interaction.startClientY) / rect.height) * 100;
        newX = clamp(newX, 0, 100);
        newY = clamp(newY, 0, 100);

        const shouldSnapX = Math.abs(newX - 50) <= 2;
        const shouldSnapY = Math.abs(newY - 50) <= 2;
        if (shouldSnapX) newX = 50;
        if (shouldSnapY) newY = 50;
        setSnapX(shouldSnapX);
        setSnapY(shouldSnapY);

        if (interaction.element === 'video') {
          onChangeConfigRef.current({ video_x: Math.round(newX), video_y: Math.round(newY) });
        } else if (interaction.element === 'avatar') {
          onChangeConfigRef.current({ avatar_x: Math.round(newX), avatar_y: Math.round(newY) });
        } else {
          onChangeConfigRef.current({ caption_x: Math.round(newX), caption_y: Math.round(newY) });
        }
        return;
      }

      const centerX = rect.left + (interaction.startX / 100) * rect.width;
      const centerY = rect.top + (interaction.startY / 100) * rect.height;

      if (interaction.mode === 'resize') {
        const distance = Math.max(1, Math.hypot(event.clientX - centerX, event.clientY - centerY));
        const ratio = distance / interaction.startDistance;
        if (interaction.element === 'video') {
          onChangeConfigRef.current({
            video_width: Math.round(clamp(interaction.startWidth * ratio, 10, 200)),
            video_height: Math.round(clamp(interaction.startHeight * ratio, 10, 200)),
          });
        } else if (interaction.element === 'avatar') {
          onChangeConfigRef.current({
            avatar_scale: Math.round(clamp(interaction.startScale * ratio, 25, 300)),
          });
        }
        return;
      }

      const currentAngle = getAngle(event.clientX, event.clientY, centerX, centerY);
      let nextRotation = interaction.startRotation + currentAngle - interaction.startAngle;
      if (event.shiftKey) nextRotation = Math.round(nextRotation / 15) * 15;
      onChangeConfigRef.current({ video_rotation: normalizeRotation(nextRotation) });
    };

    const endInteraction = () => {
      if (!interactionRef.current) return;
      interactionRef.current = null;
      setInteractionMode(null);
      setActiveElement(null);
      setSnapX(false);
      setSnapY(false);
    };

    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerup', endInteraction);
    window.addEventListener('pointercancel', endInteraction);
    return () => {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', endInteraction);
      window.removeEventListener('pointercancel', endInteraction);
    };
  }, []);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.matches('input, textarea, select, [contenteditable="true"]')) return;
      const element = selectedElementRef.current;
      if (!element || !['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;

      event.preventDefault();
      const amount = event.shiftKey ? 5 : 1;
      const current = configRef.current;
      const deltaX = event.key === 'ArrowLeft' ? -amount : event.key === 'ArrowRight' ? amount : 0;
      const deltaY = event.key === 'ArrowUp' ? -amount : event.key === 'ArrowDown' ? amount : 0;

      if (element === 'video') {
        onChangeConfigRef.current({
          video_x: clamp(current.video_x + deltaX, 0, 100),
          video_y: clamp(current.video_y + deltaY, 0, 100),
        });
      } else if (element === 'avatar') {
        onChangeConfigRef.current({
          avatar_x: clamp(current.avatar_x + deltaX, 0, 100),
          avatar_y: clamp(current.avatar_y + deltaY, 0, 100),
        });
      } else {
        onChangeConfigRef.current({
          caption_x: clamp(current.caption_x + deltaX, 0, 100),
          caption_y: clamp(current.caption_y + deltaY, 0, 100),
        });
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const renderAvatarGraphic = () => (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        width: '180px',
        height: '240px',
      }}
    >
      {config.avatar_mode === 'video' && config.avatar_media_url ? (
        <video
          key={config.avatar_media_url}
          src={config.avatar_media_url}
          autoPlay
          loop
          muted
          playsInline
          draggable={false}
          className={isSpeakingTest ? 'speaking' : ''}
          style={{
            width: '180px',
            height: '240px',
            objectFit: config.avatar_fit || 'contain',
            borderRadius: '18px',
            background: '#020617',
            filter: 'drop-shadow(0 10px 25px rgba(0,0,0,0.6))',
          }}
        />
      ) : (
        <svg
          width="180"
          height="240"
          viewBox="0 0 240 320"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={isSpeakingTest ? 'speaking' : ''}
          style={{ filter: 'drop-shadow(0 10px 25px rgba(0,0,0,0.6))' }}
        >
          <rect width="240" height="320" rx="24" fill="url(#grad_capcut)" />
          <circle cx="120" cy="110" r="50" fill="#E2E8F0" />
          <circle cx="100" cy="100" r="6" fill="#1E293B" />
          <circle cx="140" cy="100" r="6" fill="#1E293B" />
          <path
            d={isSpeakingTest ? 'M 95 125 Q 120 160 145 125 Z' : 'M 100 130 Q 120 145 140 130'}
            stroke="#1E293B"
            strokeWidth="4"
            strokeLinecap="round"
            fill={isSpeakingTest ? '#1E293B' : 'transparent'}
          />
          <path d="M 50 280 C 50 200, 190 200, 190 280 Z" fill="#8B5CF6" />
          <defs>
            <linearGradient id="grad_capcut" x1="0" y1="0" x2="240" y2="320" gradientUnits="userSpaceOnUse">
              <stop stopColor="#1E1E2E" />
              <stop offset="1" stopColor="#3B0764" />
            </linearGradient>
          </defs>
        </svg>
      )}
    </div>
  );

  const getCaptionPresetStyle = () => {
    switch (config.caption_preset) {
      case 'capcut_yellow':
        return { background: 'rgba(15, 23, 42, 0.9)', border: '2px solid #FACC15', color: '#FACC15' };
      case 'cyberpunk':
        return { background: 'rgba(24, 9, 39, 0.9)', border: '2px solid #EC4899', color: '#06B6D4' };
      case 'minimal_dark':
        return { background: 'rgba(0, 0, 0, 0.85)', border: '1px solid rgba(255, 255, 255, 0.2)', color: '#94A3B8' };
      default:
        return {
          background: config.caption_bg_color || 'rgba(15, 23, 42, 0.85)',
          border: '2px solid rgba(139, 92, 246, 0.5)',
          color: '#a78bfa',
        };
    }
  };

  const captionStyle = getCaptionPresetStyle();
  const isInteracting = Boolean(interactionMode);

  const resizeHandle = (position: React.CSSProperties, element: 'video' | 'avatar') => (
    <div
      role="button"
      aria-label="Thay đổi kích thước"
      onPointerDown={(event) => beginInteraction(event, element, 'resize')}
      style={{
        position: 'absolute',
        width: '11px',
        height: '11px',
        background: element === 'video' ? '#22d3ee' : '#8b5cf6',
        borderRadius: '2px',
        border: '1px solid #fff',
        cursor: 'nwse-resize',
        zIndex: 4,
        ...position,
      }}
    />
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#090d16', borderRadius: '16px', overflow: 'hidden', border: '1px solid var(--border-color)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', padding: '12px 20px', background: 'rgba(15, 23, 42, 0.9)', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)' }}>Tỷ lệ:</span>
          <button onClick={() => onChangeConfig({ aspect_ratio: '9:16' })} className={config.aspect_ratio === '9:16' ? 'btn-primary' : 'btn-secondary'} style={{ padding: '6px 10px', fontSize: '12px' }}>
            <Smartphone size={14} /> 9:16
          </button>
          <button onClick={() => onChangeConfig({ aspect_ratio: '16:9' })} className={config.aspect_ratio === '16:9' ? 'btn-primary' : 'btn-secondary'} style={{ padding: '6px 10px', fontSize: '12px' }}>
            <Monitor size={14} /> 16:9
          </button>
          <button onClick={() => onChangeConfig({ aspect_ratio: '1:1' })} className={config.aspect_ratio === '1:1' ? 'btn-primary' : 'btn-secondary'} style={{ padding: '6px 10px', fontSize: '12px' }}>
            <Square size={14} /> 1:1
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button onClick={() => setShowGrid((value) => !value)} className="btn-secondary" style={{ padding: '6px 10px', fontSize: '12px', borderColor: showGrid ? 'var(--accent-purple)' : undefined }}>
            <Grid size={14} /> {showGrid ? 'Tắt lưới' : 'Bật lưới'}
          </button>
          <button onClick={() => setShowTikTokOverlay((value) => !value)} className="btn-secondary" style={{ padding: '6px 10px', fontSize: '12px', borderColor: showTikTokOverlay ? 'var(--accent-cyan)' : undefined }}>
            {showTikTokOverlay ? <EyeOff size={14} /> : <Eye size={14} />} Safe zone
          </button>
          <select value={zoom} onChange={(event) => setZoom(Number(event.target.value))} aria-label="Thu phóng canvas" style={{ background: 'rgba(30, 41, 59, 0.8)', color: '#fff', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '6px 10px', fontSize: '12px' }}>
            <option value={75}>75%</option>
            <option value={100}>100%</option>
            <option value={125}>125%</option>
          </select>
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '24px', overflow: 'auto', position: 'relative', background: 'radial-gradient(circle at center, #151c2c 0%, #090d16 100%)' }}>
        <div
          ref={canvasRef}
          onPointerDown={(event) => {
            if (event.target === event.currentTarget) onSelectElement(null);
          }}
          style={{
            ...getAspectRatioStyle(),
            transform: `scale(${zoom / 100})`,
            transformOrigin: 'center center',
            backgroundColor: config.bg_mode === 'chroma_green' ? '#00FF00' : config.bg_mode === 'dark_studio' ? '#0b0f19' : '#000000',
            backgroundImage: showGrid && config.bg_mode !== 'chroma_green'
              ? 'linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px)'
              : undefined,
            backgroundSize: '20px 20px',
            position: 'relative',
            borderRadius: '16px',
            boxShadow: '0 20px 50px rgba(0,0,0,0.8), 0 0 0 1px rgba(255,255,255,0.1)',
            overflow: 'hidden',
            cursor: isInteracting ? 'grabbing' : 'default',
            userSelect: 'none',
            touchAction: 'none',
          }}
        >
          {snapX && <div style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: '2px', backgroundColor: '#22d3ee', boxShadow: '0 0 8px #22d3ee', zIndex: 100, pointerEvents: 'none' }} />}
          {snapY && <div style={{ position: 'absolute', top: '50%', left: 0, right: 0, height: '2px', backgroundColor: '#22d3ee', boxShadow: '0 0 8px #22d3ee', zIndex: 100, pointerEvents: 'none' }} />}

          {showTikTokOverlay && (
            <div style={{ position: 'absolute', inset: '5%', pointerEvents: 'none', border: '2px dashed rgba(236, 72, 153, 0.55)', borderRadius: '12px', zIndex: 40 }}>
              <div style={{ position: 'absolute', top: '8px', left: '8px', fontSize: '10px', color: '#f9a8d4', fontWeight: 'bold', background: 'rgba(0,0,0,0.65)', padding: '3px 7px', borderRadius: '4px' }}>TikTok Safe Zone</div>
            </div>
          )}

          {config.video_media_url && config.video_visible !== false && (
            <div
              onPointerDown={(event) => beginInteraction(event, 'video', 'move')}
              style={{
                position: 'absolute',
                left: `${config.video_x}%`,
                top: `${config.video_y}%`,
                width: `${config.video_width}%`,
                height: `${config.video_height}%`,
                transform: `translate(-50%, -50%) rotate(${config.video_rotation || 0}deg)`,
                transformOrigin: 'center',
                cursor: activeElement === 'video' && interactionMode === 'move' ? 'grabbing' : 'grab',
                zIndex: 5,
                border: selectedElement === 'video' ? '2px solid #22d3ee' : '2px solid transparent',
                boxShadow: selectedElement === 'video' ? '0 0 0 1px rgba(15, 23, 42, 0.9)' : undefined,
              }}
            >
              <video
                key={config.video_media_url}
                src={config.video_media_url}
                autoPlay
                loop
                muted
                playsInline
                draggable={false}
                style={{ width: '100%', height: '100%', display: 'block', objectFit: config.video_fit || 'contain', background: '#020617', pointerEvents: 'none' }}
              />
              {selectedElement === 'video' && (
                <>
                  {resizeHandle({ top: '-7px', left: '-7px' }, 'video')}
                  {resizeHandle({ top: '-7px', right: '-7px', cursor: 'nesw-resize' }, 'video')}
                  {resizeHandle({ bottom: '-7px', left: '-7px', cursor: 'nesw-resize' }, 'video')}
                  {resizeHandle({ bottom: '-7px', right: '-7px' }, 'video')}
                  <div style={{ position: 'absolute', left: '50%', top: '0', width: '1px', height: '22px', background: '#22d3ee', transform: 'translateX(-50%)', pointerEvents: 'none' }} />
                  <div role="button" aria-label="Xoay video" onPointerDown={(event) => beginInteraction(event, 'video', 'rotate')} style={{ position: 'absolute', left: '50%', top: '14px', width: '15px', height: '15px', borderRadius: '50%', border: '2px solid #fff', background: '#22d3ee', transform: 'translateX(-50%)', cursor: 'grab', zIndex: 5 }} />
                  <div style={{ position: 'absolute', top: '36px', left: '50%', transform: 'translateX(-50%)', background: '#0891b2', color: '#fff', fontSize: '10px', padding: '3px 7px', borderRadius: '4px', fontWeight: 700, whiteSpace: 'nowrap', pointerEvents: 'none' }}>
                    Video · {config.video_rotation || 0}°
                  </div>
                </>
              )}
            </div>
          )}

          {config.avatar_visible !== false && (
            <div
              onPointerDown={(event) => beginInteraction(event, 'avatar', 'move')}
              style={{
                position: 'absolute',
                left: `${config.avatar_x}%`,
                top: `${config.avatar_y}%`,
                transform: `translate(-50%, -50%) scale(${(config.avatar_scale || 100) / 100})`,
                transformOrigin: 'center',
                cursor: activeElement === 'avatar' && interactionMode === 'move' ? 'grabbing' : 'grab',
                zIndex: 10,
                padding: '6px',
                border: selectedElement === 'avatar' ? '2px dashed #8b5cf6' : '2px solid transparent',
                borderRadius: '12px',
              }}
            >
              {renderAvatarGraphic()}
              {selectedElement === 'avatar' && (
                <>
                  {resizeHandle({ top: '-7px', left: '-7px' }, 'avatar')}
                  {resizeHandle({ top: '-7px', right: '-7px', cursor: 'nesw-resize' }, 'avatar')}
                  {resizeHandle({ bottom: '-7px', left: '-7px', cursor: 'nesw-resize' }, 'avatar')}
                  {resizeHandle({ bottom: '-7px', right: '-7px' }, 'avatar')}
                  <div style={{ position: 'absolute', top: '-26px', left: '50%', transform: 'translateX(-50%)', background: '#8b5cf6', color: '#fff', fontSize: '10px', padding: '3px 7px', borderRadius: '4px', fontWeight: 700, whiteSpace: 'nowrap', pointerEvents: 'none' }}>
                    MC Avatar · {config.avatar_scale || 100}%
                  </div>
                </>
              )}
            </div>
          )}

          {config.caption_visible !== false && (
            <div
              onPointerDown={(event) => beginInteraction(event, 'caption', 'move')}
              style={{
                position: 'absolute',
                left: `${config.caption_x}%`,
                top: `${config.caption_y}%`,
                transform: 'translate(-50%, -50%)',
                width: '85%',
                maxWidth: '500px',
                cursor: activeElement === 'caption' && interactionMode === 'move' ? 'grabbing' : 'grab',
                zIndex: 20,
                padding: '6px',
                border: selectedElement === 'caption' ? '2px dashed #06b6d4' : '2px solid transparent',
                borderRadius: '14px',
              }}
            >
              <div style={{ background: captionStyle.background, border: captionStyle.border, borderRadius: '14px', padding: '14px 20px', textAlign: 'center', boxShadow: '0 10px 25px rgba(0,0,0,0.5)', backdropFilter: 'blur(8px)' }}>
                <div style={{ fontSize: '12px', fontWeight: 'bold', color: captionStyle.color, textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '4px' }}>
                  Trả lời: Nguyễn Văn A
                </div>
                <div style={{ fontSize: `${config.caption_font_size || 18}px`, fontWeight: 600, color: config.caption_text_color || '#f3f4f6', lineHeight: 1.4 }}>
                  Sẵn sàng phản hồi bình luận khán giả trên livestream!
                </div>
              </div>
              {selectedElement === 'caption' && (
                <div style={{ position: 'absolute', top: '-26px', left: '50%', transform: 'translateX(-50%)', background: '#06b6d4', color: '#fff', fontSize: '10px', padding: '3px 7px', borderRadius: '4px', fontWeight: 700, whiteSpace: 'nowrap', pointerEvents: 'none' }}>
                  Phụ đề · {config.caption_x}%, {config.caption_y}%
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
