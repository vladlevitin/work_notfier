import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, Post } from '../api/client';
import './PostDetail.css';

export function PostDetailPage() {
  const { postId } = useParams<{ postId: string }>();
  const navigate = useNavigate();
  const [post, setPost] = useState<Post | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadPost = async () => {
      if (!postId) {
        setError('No post ID provided');
        setLoading(false);
        return;
      }

      try {
        const postData = await api.getPostById(postId);
        setPost(postData);
      } catch (err: any) {
        setError(err.message || 'Failed to load post');
      } finally {
        setLoading(false);
      }
    };

    loadPost();
  }, [postId]);

  // Format scraped_at date
  const formatDate = (isoString: string): string => {
    try {
      const date = new Date(isoString);
      return date.toLocaleString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return isoString;
    }
  };

  // Get category display with icon
  const getCategoryDisplay = (post: Post) => {
    if (post.category) {
      const categoryIcons: Record<string, string> = {
        'Transport': '🚚',
        'Moving': '🚚',
        'Painting': '🎨',
        'Renovation': '🎨',
        'Cleaning': '🧹',
        'Garden': '🧹',
        'Plumbing': '🔧',
        'Electrical': '🔧',
        'Assembly': '🪑',
        'Furniture': '🪑',
        'General': '📦'
      };
      
      const icon = Object.entries(categoryIcons).find(([key]) => 
        post.category?.includes(key)
      )?.[1] || '📦';
      
      return { icon, name: post.category };
    }
    
    // Fallback: keyword-based categorization
    const content = (post.title + ' ' + post.text).toLowerCase();
    if (content.match(/(flytte|bære|transport|frakte|hente|kjøre|bil|henger)/)) return { icon: '🚚', name: 'Transport / Moving' };
    if (content.match(/(male|sparkle|pusse|oppussing|renovere|snekker|gulv|vegg)/)) return { icon: '🎨', name: 'Painting / Renovation' };
    if (content.match(/(vask|rengjøring|utvask|hage|klippe|måke|snø)/)) return { icon: '🧹', name: 'Cleaning / Garden' };
    if (content.match(/(rørlegger|elektriker|strøm|vann|vvs|lys)/)) return { icon: '🔧', name: 'Plumbing / Electrical' };
    if (content.match(/(montere|demontere|ikea|møbler|skap|seng|sofa)/)) return { icon: '🪑', name: 'Assembly / Furniture' };
    
    return { icon: '📦', name: 'General' };
  };

  if (loading) {
    return (
      <div className="detail-container">
        <div className="loading">Loading post details...</div>
      </div>
    );
  }

  if (error || !post) {
    return (
      <div className="detail-container">
        <div className="error-state">
          <h2>Post Not Found</h2>
          <p>{error || 'The post you are looking for does not exist.'}</p>
          <button onClick={() => navigate('/')} className="back-button">
            ← Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const category = getCategoryDisplay(post);

  return (
    <div className="detail-container">
      <button onClick={() => navigate('/')} className="back-button">
        ← Back to Dashboard
      </button>

      <div className="detail-card">
        {/* Header Section */}
        <div className="detail-header">
          <div className="detail-badges">
            <span className="category-badge large">
              {category.icon} {category.name}
            </span>
            {post.location && (
              <span className="location-badge large">
                📍 {post.location}
              </span>
            )}
            {post.notified === 1 && (
              <span className="notified-badge large">✅ Notified</span>
            )}
          </div>
          
          <h1 className="detail-title">{post.title}</h1>
          
          <div className="detail-timestamp">
            🕒 Posted: {post.timestamp}
          </div>
        </div>

        {/* Full Text Section */}
        <div className="detail-content">
          <h2>Full Post Content</h2>
          <div className="detail-text">
            {post.text}
          </div>
        </div>

        {/* Metadata Section */}
        <div className="detail-meta">
          <h2>Post Details</h2>
          
          <div className="meta-grid">
            <div className="meta-item">
              <span className="meta-label">Post ID</span>
              <span className="meta-value">{post.post_id}</span>
            </div>
            
            <div className="meta-item">
              <span className="meta-label">Facebook Group</span>
              <a 
                href={post.group_url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="meta-link"
              >
                {post.group_name}
              </a>
            </div>
            
            <div className="meta-item">
              <span className="meta-label">Scraped At</span>
              <span className="meta-value">{formatDate(post.scraped_at)}</span>
            </div>
            
            <div className="meta-item">
              <span className="meta-label">Status</span>
              <span className="meta-value">
                {post.notified === 1 ? '✅ Email Sent' : '🆕 New Post'}
              </span>
            </div>

            {post.ai_processed && (
              <div className="meta-item">
                <span className="meta-label">AI Processed</span>
                <span className="meta-value">✓ Yes</span>
              </div>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="detail-actions">
          <a 
            href={post.url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="primary-button"
          >
            🔗 View on Facebook
          </a>
          
          <a 
            href={post.group_url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="secondary-button"
          >
            👥 View Group
          </a>
        </div>
      </div>
    </div>
  );
}
