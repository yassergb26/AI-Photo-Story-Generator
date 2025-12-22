import React, { useState } from 'react';
import EmotionChart from './EmotionChart';
import EmotionBadge from './EmotionBadge';
import './StoryDetail.css';

const StoryDetail = ({ story, onClose, onUpdate, onDelete, detectingEmotions }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedTitle, setEditedTitle] = useState(story.title);
  const [editedDescription, setEditedDescription] = useState(story.description || '');
  const [saving, setSaving] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [selectedTone, setSelectedTone] = useState(story.narrative_tone || 'joyful');
  const [showToneSelector, setShowToneSelector] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    const success = await onUpdate(story.id, {
      title: editedTitle,
      description: editedDescription,
    });

    if (success) {
      setIsEditing(false);
    }
    setSaving(false);
  };

  const handleCancel = () => {
    setEditedTitle(story.title);
    setEditedDescription(story.description || '');
    setIsEditing(false);
  };

  const handleDelete = async () => {
    await onDelete(story.id);
  };

  const handleRegenerateNarrative = async () => {
    setRegenerating(true);
    setShowToneSelector(false);

    try {
      const response = await fetch(`/api/narratives/${story.id}/regenerate?narrative_tone=${selectedTone}&use_llm=true`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (response.ok) {
        const data = await response.json();
        // Update the story with new narrative
        await onUpdate(story.id, {
          title: data.title,
          description: data.description,
          narrative_tone: data.tone
        });
      }
    } catch (error) {
      console.error('Error regenerating narrative:', error);
      alert('Failed to regenerate narrative. Please try again.');
    } finally {
      setRegenerating(false);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getPatternTypeLabel = () => {
    if (!story.story_metadata?.pattern_type) return null;

    const type = story.story_metadata.pattern_type;
    const frequency = story.story_metadata.pattern_frequency;

    const labels = {
      temporal: `Temporal Pattern ${frequency ? `(${frequency})` : ''}`,
      spatial: 'Location-based Pattern',
      visual: 'Visual Theme Pattern'
    };

    return labels[type] || 'Pattern-based Story';
  };

  return (
    <div className="story-modal-overlay" onClick={onClose}>
      <div className="story-modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close-btn" onClick={onClose}>×</button>

        <div className="story-detail-header">
          {isEditing ? (
            <input
              type="text"
              className="edit-title-input"
              value={editedTitle}
              onChange={(e) => setEditedTitle(e.target.value)}
              placeholder="Story title"
            />
          ) : (
            <h2>{story.title}</h2>
          )}

          <div className="story-metadata">
            {getPatternTypeLabel() && (
              <span className="pattern-label">{getPatternTypeLabel()}</span>
            )}
            <span className="story-date-time">
              Created: {formatDate(story.created_at)}
            </span>
          </div>
        </div>

        <div className="story-detail-content">
          {isEditing ? (
            <textarea
              className="edit-description-textarea"
              value={editedDescription}
              onChange={(e) => setEditedDescription(e.target.value)}
              placeholder="Story description"
              rows={6}
            />
          ) : (
            <>
              <p className="story-full-description">{story.description}</p>

              {/* Narrative Regeneration UI */}
              <div className="narrative-controls">
                {story.story_metadata?.generation_method === 'llm_generated' && (
                  <span className="generation-method-badge">🤖 AI Generated</span>
                )}
                {story.narrative_tone && (
                  <span className="current-tone-badge">Tone: {story.narrative_tone}</span>
                )}
                <button
                  className="regenerate-btn"
                  onClick={() => setShowToneSelector(!showToneSelector)}
                  disabled={regenerating}
                >
                  {regenerating ? 'Regenerating...' : '🔄 Regenerate Narrative'}
                </button>
              </div>

              {showToneSelector && (
                <div className="tone-selector">
                  <label>Select narrative tone:</label>
                  <div className="tone-options">
                    {['joyful', 'nostalgic', 'celebratory', 'reflective'].map((tone) => (
                      <button
                        key={tone}
                        className={`tone-option ${selectedTone === tone ? 'selected' : ''}`}
                        onClick={() => setSelectedTone(tone)}
                      >
                        {tone === 'joyful' && '😊 Joyful'}
                        {tone === 'nostalgic' && '🌅 Nostalgic'}
                        {tone === 'celebratory' && '🎉 Celebratory'}
                        {tone === 'reflective' && '💭 Reflective'}
                      </button>
                    ))}
                  </div>
                  <button
                    className="apply-tone-btn"
                    onClick={handleRegenerateNarrative}
                    disabled={regenerating}
                  >
                    Generate with {selectedTone} tone
                  </button>
                </div>
              )}
            </>
          )}

          {/* Emotion Chart Section */}
          {detectingEmotions ? (
            <div className="emotions-section">
              <h3>Emotions in this story</h3>
              <div className="emotions-loading">
                <p>🔍 Detecting emotions in images...</p>
              </div>
            </div>
          ) : story.emotions && story.emotions.length > 0 ? (
            <div className="emotions-section">
              <h3>Emotions in this story</h3>
              <div className="emotions-display">
                <EmotionChart emotions={story.emotions} type="bar" showLabels={true} />
              </div>
              <div className="emotion-badges">
                {story.emotions.slice(0, 3).map((emotion, idx) => (
                  <EmotionBadge
                    key={idx}
                    emotion={emotion.emotion || emotion.name}
                    percentage={emotion.percentage}
                    size="medium"
                  />
                ))}
              </div>
            </div>
          ) : null}

          <div className="story-images-section">
            <h3>Photos in this story ({story.images?.length || 0})</h3>
            <div className="story-images-grid">
              {story.images && story.images.length > 0 ? (
                story.images.map((image) => (
                  <div key={image.id} className="story-image-item">
                    <img
                      src={`http://localhost:8000${image.file_path.replace('./', '/')}`}
                      alt={image.filename}
                      className="story-image"
                    />
                    <div className="story-image-caption">
                      {image.filename}
                    </div>
                  </div>
                ))
              ) : (
                <p className="no-images">No images in this story</p>
              )}
            </div>
          </div>
        </div>

        <div className="story-detail-actions">
          {isEditing ? (
            <>
              <button
                className="save-btn"
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
              <button
                className="cancel-btn"
                onClick={handleCancel}
                disabled={saving}
              >
                Cancel
              </button>
            </>
          ) : (
            <>
              <button className="edit-btn" onClick={() => setIsEditing(true)}>
                Edit Story
              </button>
              <button className="delete-btn" onClick={handleDelete}>
                Delete Story
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default StoryDetail;
