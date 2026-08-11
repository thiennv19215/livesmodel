import React from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Eye,
  EyeOff,
  Film,
  Layers,
  LoaderCircle,
  Plus,
  Trash2,
  Type,
  Upload,
  User,
} from 'lucide-react';

export type CapCutSourceElement = 'video' | 'avatar' | 'caption';

export interface CapCutSourcesConfig {
  video_media_url: string;
  video_name: string;
  video_visible: boolean;
  avatar_visible: boolean;
  caption_visible: boolean;
}

export interface CapCutSourcesPanelProps {
  config: CapCutSourcesConfig;
  selectedElement: CapCutSourceElement | null;
  onSelectElement: (element: CapCutSourceElement) => void;
  onChangeConfig: (newConfig: Partial<CapCutSourcesConfig>) => void;
  onUploadVideo: (file: File) => void;
  onRemoveVideo?: () => void;
  isUploadingVideo?: boolean;
  videoUploadError?: string | null;
  videoUploadSuccess?: boolean;
}

interface SourceRowProps {
  element: CapCutSourceElement;
  selectedElement: CapCutSourceElement | null;
  accentColor: string;
  selectedBackground: string;
  iconBackground: string;
  icon: React.ReactNode;
  title: string;
  subtitle: string;
  visible?: boolean;
  actions?: React.ReactNode;
  onSelectElement: (element: CapCutSourceElement) => void;
}

const getMediaName = (mediaUrl: string) => {
  const rawName = mediaUrl.split('/').filter(Boolean).pop();
  if (!rawName) return 'Video đã tải';

  try {
    return decodeURIComponent(rawName);
  } catch {
    return rawName;
  }
};

const SourceRow: React.FC<SourceRowProps> = ({
  element,
  selectedElement,
  accentColor,
  selectedBackground,
  iconBackground,
  icon,
  title,
  subtitle,
  visible = true,
  actions,
  onSelectElement,
}) => {
  const isSelected = selectedElement === element;

  return (
    <div
      role="button"
      tabIndex={0}
      aria-pressed={isSelected}
      onClick={() => onSelectElement(element)}
      onKeyDown={(event) => {
        if (event.target !== event.currentTarget) return;
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onSelectElement(element);
        }
      }}
      style={{
        minHeight: '62px',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        padding: '9px 10px',
        borderRadius: '11px',
        border: isSelected ? `1px solid ${accentColor}` : '1px solid var(--border-color)',
        background: isSelected ? selectedBackground : 'rgba(15, 23, 42, 0.62)',
        opacity: visible ? 1 : 0.58,
        cursor: 'pointer',
        outline: 'none',
      }}
    >
      <div
        style={{
          width: '42px',
          height: '42px',
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: '9px',
          background: iconBackground,
          color: accentColor,
        }}
      >
        {icon}
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          title={title}
          style={{
            overflow: 'hidden',
            color: '#f8fafc',
            fontSize: '12px',
            fontWeight: 700,
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {title}
        </div>
        <div
          title={subtitle}
          style={{
            marginTop: '3px',
            overflow: 'hidden',
            color: 'var(--text-secondary)',
            fontSize: '10px',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {subtitle}
        </div>
      </div>

      {actions}
    </div>
  );
};

export const CapCutSourcesPanel: React.FC<CapCutSourcesPanelProps> = ({
  config,
  selectedElement,
  onSelectElement,
  onChangeConfig,
  onUploadVideo,
  onRemoveVideo,
  isUploadingVideo = false,
  videoUploadError,
  videoUploadSuccess = false,
}) => {
  const hasVideo = Boolean(config.video_media_url);
  const videoVisible = config.video_visible !== false;
  const avatarVisible = config.avatar_visible !== false;
  const captionVisible = config.caption_visible !== false;
  const videoTitle = config.video_name.trim() || getMediaName(config.video_media_url);

  const removeVideo = () => {
    if (onRemoveVideo) {
      onRemoveVideo();
    } else {
      onChangeConfig({
        video_media_url: '',
        video_name: '',
        video_visible: true,
      });
    }
    onSelectElement('avatar');
  };

  return (
    <aside
      aria-label="Nguồn và lớp cảnh"
      style={{
        width: '288px',
        minWidth: '250px',
        maxWidth: '320px',
        height: '100%',
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        background: '#0e1526',
        border: '1px solid var(--border-color)',
        borderRadius: '16px',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 14px',
          background: 'rgba(15, 23, 42, 0.95)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Layers size={16} color="var(--accent-purple)" />
          <span style={{ fontSize: '13px', fontWeight: 700 }}>Nguồn</span>
        </div>
        <span
          style={{
            minWidth: '22px',
            padding: '2px 7px',
            borderRadius: '999px',
            background: 'rgba(139, 92, 246, 0.16)',
            color: '#c4b5fd',
            fontSize: '11px',
            fontWeight: 700,
            textAlign: 'center',
          }}
        >
          {hasVideo ? 3 : 2}
        </span>
      </div>

      <div
        style={{
          flex: 1,
          minHeight: 0,
          overflowY: 'auto',
          padding: '12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
        }}
      >
        <label
          className="btn-primary"
          aria-disabled={isUploadingVideo}
          style={{
            width: '100%',
            minHeight: '40px',
            padding: '9px 12px',
            justifyContent: 'center',
            cursor: isUploadingVideo ? 'wait' : 'pointer',
            opacity: isUploadingVideo ? 0.75 : 1,
            fontSize: '12px',
          }}
        >
          {isUploadingVideo ? (
            <LoaderCircle size={16} className="animate-spin" />
          ) : (
            <Plus size={17} />
          )}
          {isUploadingVideo ? 'Đang tải video...' : hasVideo ? 'Thay video nguồn' : 'Thêm video nguồn'}
          <input
            type="file"
            accept="video/mp4,video/webm,.mp4,.webm"
            disabled={isUploadingVideo}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) onUploadVideo(file);
              event.currentTarget.value = '';
            }}
            style={{ display: 'none' }}
          />
        </label>

        {videoUploadError && (
          <div
            role="alert"
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '7px',
              padding: '8px 9px',
              borderRadius: '8px',
              background: 'rgba(239, 68, 68, 0.1)',
              color: '#fca5a5',
              fontSize: '11px',
              lineHeight: 1.4,
            }}
          >
            <AlertCircle size={14} style={{ flexShrink: 0, marginTop: '1px' }} />
            <span>{videoUploadError}</span>
          </div>
        )}

        {videoUploadSuccess && !videoUploadError && (
          <div
            role="status"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '7px',
              padding: '8px 9px',
              borderRadius: '8px',
              background: 'rgba(34, 197, 94, 0.1)',
              color: '#86efac',
              fontSize: '11px',
              lineHeight: 1.4,
            }}
          >
            <CheckCircle2 size={14} style={{ flexShrink: 0 }} />
            <span>Đã thêm video thành một nguồn riêng.</span>
          </div>
        )}

        {hasVideo && (
          <SourceRow
            element="video"
            selectedElement={selectedElement}
            accentColor="#fb923c"
            selectedBackground="rgba(249, 115, 22, 0.14)"
            iconBackground="linear-gradient(145deg, rgba(249, 115, 22, 0.3), rgba(30, 41, 59, 0.85))"
            icon={<Film size={20} />}
            title={videoTitle}
            subtitle="Video nguồn độc lập"
            visible={videoVisible}
            onSelectElement={onSelectElement}
            actions={
              <div style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                <button
                  type="button"
                  title={videoVisible ? 'Ẩn video' : 'Hiện video'}
                  aria-label={videoVisible ? 'Ẩn video' : 'Hiện video'}
                  aria-pressed={!videoVisible}
                  onClick={(event) => {
                    event.stopPropagation();
                    onChangeConfig({ video_visible: !videoVisible });
                  }}
                  style={{
                    width: '28px',
                    height: '28px',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: 0,
                    border: 'none',
                    borderRadius: '7px',
                    background: 'transparent',
                    color: videoVisible ? '#cbd5e1' : '#64748b',
                    cursor: 'pointer',
                  }}
                >
                  {videoVisible ? <Eye size={15} /> : <EyeOff size={15} />}
                </button>
                <button
                  type="button"
                  title="Gỡ video khỏi cảnh"
                  aria-label="Gỡ video khỏi cảnh"
                  onClick={(event) => {
                    event.stopPropagation();
                    removeVideo();
                  }}
                  style={{
                    width: '28px',
                    height: '28px',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: 0,
                    border: 'none',
                    borderRadius: '7px',
                    background: 'transparent',
                    color: '#fca5a5',
                    cursor: 'pointer',
                  }}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            }
          />
        )}

        <SourceRow
          element="avatar"
          selectedElement={selectedElement}
          accentColor="#a78bfa"
          selectedBackground="rgba(139, 92, 246, 0.16)"
          iconBackground="linear-gradient(145deg, rgba(139, 92, 246, 0.3), rgba(30, 41, 59, 0.85))"
          icon={<User size={20} />}
          title="MC Avatar"
          subtitle="Avatar dựng sẵn"
          visible={avatarVisible}
          onSelectElement={onSelectElement}
          actions={
            <button
              type="button"
              title={avatarVisible ? 'Ẩn avatar' : 'Hiện avatar'}
              aria-label={avatarVisible ? 'Ẩn avatar' : 'Hiện avatar'}
              aria-pressed={!avatarVisible}
              onClick={(event) => {
                event.stopPropagation();
                onChangeConfig({ avatar_visible: !avatarVisible });
              }}
              style={{
                width: '28px',
                height: '28px',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: 0,
                border: 'none',
                borderRadius: '7px',
                background: 'transparent',
                color: avatarVisible ? '#cbd5e1' : '#64748b',
                cursor: 'pointer',
              }}
            >
              {avatarVisible ? <Eye size={15} /> : <EyeOff size={15} />}
            </button>
          }
        />

        <SourceRow
          element="caption"
          selectedElement={selectedElement}
          accentColor="#67e8f9"
          selectedBackground="rgba(6, 182, 212, 0.14)"
          iconBackground="linear-gradient(145deg, rgba(6, 182, 212, 0.25), rgba(30, 41, 59, 0.85))"
          icon={<Type size={20} />}
          title="Khung phụ đề"
          subtitle="Caption động từ TTS"
          visible={captionVisible}
          onSelectElement={onSelectElement}
          actions={
            <button
              type="button"
              title={captionVisible ? 'Ẩn phụ đề' : 'Hiện phụ đề'}
              aria-label={captionVisible ? 'Ẩn phụ đề' : 'Hiện phụ đề'}
              aria-pressed={!captionVisible}
              onClick={(event) => {
                event.stopPropagation();
                onChangeConfig({ caption_visible: !captionVisible });
              }}
              style={{
                width: '28px',
                height: '28px',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: 0,
                border: 'none',
                borderRadius: '7px',
                background: 'transparent',
                color: captionVisible ? '#cbd5e1' : '#64748b',
                cursor: 'pointer',
              }}
            >
              {captionVisible ? <Eye size={15} /> : <EyeOff size={15} />}
            </button>
          }
        />

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '7px',
            marginTop: '2px',
            padding: '8px 9px',
            borderRadius: '8px',
            background: 'rgba(255, 255, 255, 0.025)',
            color: 'var(--text-secondary)',
            fontSize: '10px',
            lineHeight: 1.45,
          }}
        >
          <Upload size={13} style={{ flexShrink: 0 }} />
          Chọn một nguồn để kéo, đổi kích thước hoặc xoay trên khung xem trước.
        </div>
      </div>
    </aside>
  );
};
