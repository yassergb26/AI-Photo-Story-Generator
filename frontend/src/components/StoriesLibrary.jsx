import React, { useState, useEffect } from 'react';
import StoryCard from './StoryCard';
import StoryDetail from './StoryDetail';
import './StoriesLibrary.css';

const StoriesLibrary = ({ userId, refreshTrigger }) => {
  const [stories, setStories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedStory, setSelectedStory] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [detectingEmotions, setDetectingEmotions] = useState(false);

  useEffect(() => {
    fetchStories();
  }, [userId, refreshTrigger]);

  const fetchStories = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/stories/?user_id=${userId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch stories');
      }
      const data = await response.json();
      setStories(data);
    } catch (err) {
      console.error('Error fetching stories:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const generateStories = async () => {
    setGenerating(true);
    setError(null);
    try {
      const response = await fetch('/api/stories/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          force_regenerate: false,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.message || 'Failed to generate stories');
      }

      if (data.success) {
        // Refresh stories list
        await fetchStories();
        if (data.stories_generated > 0) {
          alert(`Successfully generated ${data.stories_generated} new stories!`);
        } else {
          alert('No new stories were generated. Make sure you have detected patterns first.');
        }
      } else {
        // Handle unsuccessful response with message
        alert(data.message || 'Failed to generate stories. Please detect patterns first.');
      }
    } catch (err) {
      console.error('Error generating stories:', err);
      setError(err.message);
      alert(err.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleStoryClick = async (story) => {
    try {
      // Fetch full story details with images
      const response = await fetch(`/api/stories/${story.id}`);
      if (!response.ok) {
        throw new Error('Failed to fetch story details');
      }
      const detailedStory = await response.json();

      // Fetch emotions for this story
      let emotionsData = null;
      try {
        const emotionsResponse = await fetch(`/api/emotions/story/${story.id}`);
        if (emotionsResponse.ok) {
          emotionsData = await emotionsResponse.json();
          detailedStory.emotions = emotionsData.emotions;
        }
      } catch (emotionErr) {
        console.warn('Could not fetch emotions for story:', emotionErr);
      }

      // If no emotions found, automatically detect them for all images
      if (!emotionsData || !emotionsData.emotions || emotionsData.emotions.length === 0) {
        console.log('No emotions found, detecting emotions for story images...');
        setDetectingEmotions(true);

        if (detailedStory.images && detailedStory.images.length > 0) {
          // Detect emotions for each image
          const detectionPromises = detailedStory.images.map(image =>
            fetch(`/api/emotions/detect/${image.id}`, { method: 'POST' })
              .then(res => res.ok ? res.json() : null)
              .catch(err => {
                console.warn(`Failed to detect emotions for image ${image.id}:`, err);
                return null;
              })
          );

          await Promise.all(detectionPromises);

          // Aggregate emotions for the story
          try {
            const aggregateResponse = await fetch(`/api/emotions/story/${story.id}/aggregate`, {
              method: 'POST'
            });

            if (aggregateResponse.ok) {
              // Fetch the aggregated emotions
              const emotionsResponse = await fetch(`/api/emotions/story/${story.id}`);
              if (emotionsResponse.ok) {
                const newEmotionsData = await emotionsResponse.json();
                detailedStory.emotions = newEmotionsData.emotions;
              }
            }
          } catch (aggregateErr) {
            console.warn('Failed to aggregate emotions:', aggregateErr);
          }
        }

        setDetectingEmotions(false);
      }

      setSelectedStory(detailedStory);
    } catch (err) {
      console.error('Error fetching story details:', err);
      setError(err.message);
    }
  };

  const handleCloseModal = () => {
    setSelectedStory(null);
  };

  const handleUpdateStory = async (storyId, updates) => {
    try {
      const response = await fetch(`/api/stories/${storyId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates),
      });

      if (!response.ok) {
        throw new Error('Failed to update story');
      }

      // Refresh stories and update selected story
      await fetchStories();

      const updatedResponse = await fetch(`/api/stories/${storyId}`);
      const updatedStory = await updatedResponse.json();

      // Fetch emotions for updated story
      try {
        const emotionsResponse = await fetch(`/api/emotions/story/${storyId}`);
        if (emotionsResponse.ok) {
          const emotionsData = await emotionsResponse.json();
          updatedStory.emotions = emotionsData.emotions;
        }
      } catch (emotionErr) {
        console.warn('Could not fetch emotions for story:', emotionErr);
      }

      setSelectedStory(updatedStory);

      return true;
    } catch (err) {
      console.error('Error updating story:', err);
      setError(err.message);
      return false;
    }
  };

  const handleDeleteStory = async (storyId) => {
    if (!window.confirm('Are you sure you want to delete this story?')) {
      return false;
    }

    try {
      const response = await fetch(`/api/stories/${storyId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete story');
      }

      // Close modal and refresh stories
      setSelectedStory(null);
      await fetchStories();

      return true;
    } catch (err) {
      console.error('Error deleting story:', err);
      setError(err.message);
      return false;
    }
  };

  return (
    <div className="stories-library">
      <div className="stories-header">
        <h2>Your Stories ({stories.length})</h2>
        <button
          className="generate-btn"
          onClick={generateStories}
          disabled={generating}
        >
          {generating ? 'Generating...' : '✨ Generate New Stories'}
        </button>
      </div>

      {error && (
        <div className="error-message">
          Error: {error}
        </div>
      )}

      {loading ? (
        <div className="loading">Loading stories...</div>
      ) : stories.length === 0 ? (
        <div className="empty-state">
          <p>No stories yet!</p>
          <p>Generate stories from your detected patterns to create beautiful narratives.</p>
          <button className="generate-btn" onClick={generateStories}>
            ✨ Generate Stories
          </button>
        </div>
      ) : (
        <div className="stories-grid">
          {stories.map((story) => (
            <StoryCard
              key={story.id}
              story={story}
              onClick={() => handleStoryClick(story)}
            />
          ))}
        </div>
      )}

      {selectedStory && (
        <StoryDetail
          story={selectedStory}
          onClose={handleCloseModal}
          onUpdate={handleUpdateStory}
          onDelete={handleDeleteStory}
          detectingEmotions={detectingEmotions}
        />
      )}
    </div>
  );
};

export default StoriesLibrary;
