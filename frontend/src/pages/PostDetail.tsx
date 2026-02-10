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

  // Format date in detail
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

  // Get display timestamp - prefer posted_at over relative timestamp
  const getDisplayTimestamp = (post: Post): string => {
    if (post.posted_at) {
      return formatDate(post.posted_at);
    }
    return post.timestamp;
  };

  // Get direct post URL - construct from post_id if the stored URL is just the group URL
  const getPostUrl = (post: Post): string => {
    // If the stored URL already points to a specific post, use it
    if (post.url && post.url !== post.group_url && 
        (post.url.includes('/posts/') || post.url.includes('/permalink/') || post.url.includes('story_fbid='))) {
      return post.url;
    }
    
    // Try to construct a direct post URL from the post_id
    // Only works for numeric post IDs or pfbid format (not hash-based h_ IDs)
    if (post.post_id && !post.post_id.startsWith('h_')) {
      // Extract group ID from group_url
      const groupIdMatch = post.group_url.match(/\/groups\/(\d+)/);
      if (groupIdMatch) {
        return `https://www.facebook.com/groups/${groupIdMatch[1]}/posts/${post.post_id}`;
      }
    }
    
    // Fallback to stored URL (may be group URL for hash-ID posts)
    return post.url;
  };

  // Check if we have a direct link to the post (not just the group)
  const hasDirectPostUrl = (post: Post): boolean => {
    const url = getPostUrl(post);
    return url !== post.group_url;
  };

  const categoryIcons: Record<string, string> = {
    'Electrical': '⚡',
    'Plumbing': '🔧',
    'Transport / Moving': '🚚',
    'Manual Labor': '🏗️',
    'Painting / Renovation': '🎨',
    'Cleaning / Garden': '🧹',
    'Assembly / Furniture': '🪑',
    'Car Mechanic': '🔩',
    'Handyman / Misc': '🔨',
    'IT / Tech': '💻',
    'Other': '📦',
  };

  const getIconForCategory = (cat: string): string => {
    return categoryIcons[cat] || 
      Object.entries(categoryIcons).find(([key]) => cat.includes(key))?.[1] || 
      '📦';
  };

  const getSecondaryCategories = (post: Post): string[] => {
    if (!post.secondary_categories) return [];
    try {
      const parsed = JSON.parse(post.secondary_categories);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  };

  const getCategoryDisplay = (post: Post): { icon: string; name: string } => {
    if (post.category && post.category !== 'Other' && post.category !== 'General') {
      return { icon: getIconForCategory(post.category), name: post.category };
    }

    const content = (post.title + ' ' + post.text).toLowerCase();
    if (content.match(/(flytte|bære|transport|frakte|hente|kjøre|henger)/)) return { icon: '🚚', name: 'Transport / Moving' };
    if (content.match(/(male|sparkle|pusse|oppussing|renovere|snekker|gulv|vegg|fliser|tapet)/)) return { icon: '🎨', name: 'Painting / Renovation' };
    if (content.match(/(vask|rengjøring|utvask|hage|klippe|måke|snø)/)) return { icon: '🧹', name: 'Cleaning / Garden' };
    if (content.match(/(rørlegger|rør|avløp|toalett|dusj|vann|vvs)/)) return { icon: '🔧', name: 'Plumbing' };
    if (content.match(/(elektriker|strøm|sikring|lys|stikkontakt|kurs)/)) return { icon: '⚡', name: 'Electrical' };
    if (content.match(/(montere|demontere|ikea|møbler|skap|seng|hylle|tv.*vegg)/)) return { icon: '🪑', name: 'Assembly / Furniture' };
    if (content.match(/(bil|motor|bremse|dekk|verksted|mekaniker|eu.*kontroll)/)) return { icon: '🔩', name: 'Car Mechanic' };
    if (content.match(/(pc|data|mobil|skjerm|printer|wifi|internett|smart.*hjem)/)) return { icon: '💻', name: 'IT / Tech' };
    if (content.match(/(løfte|bære|tungt|rive|demoler|rydde|kaste)/)) return { icon: '🏗️', name: 'Manual Labor' };
    if (content.match(/(reparere|fikse|bytte|ordne|småjobb)/)) return { icon: '🔨', name: 'Handyman / Misc' };

    return { icon: '📦', name: 'Other' };
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
  const secondaryCats = getSecondaryCategories(post);

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
            {secondaryCats.length > 0 && secondaryCats.map(s => (
              <span key={s} className="category-badge large secondary">
                {getIconForCategory(s)} {s}
              </span>
            ))}
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
            🕒 Posted: {getDisplayTimestamp(post)}
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
                {post.group_name.replace(/^\(\d+\)\s*/, '')}
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
            href={getPostUrl(post)} 
            target="_blank" 
            rel="noopener noreferrer"
            className="primary-button"
          >
            🔗 {hasDirectPostUrl(post) ? 'View Post on Facebook' : 'View on Facebook (Group)'}
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
