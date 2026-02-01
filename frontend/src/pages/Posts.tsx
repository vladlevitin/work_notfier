import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, Post, Stats } from '../api/client';
import './Posts.css';

const PAGE_SIZE = 20;

export function PostsPage() {
  const navigate = useNavigate();
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [stats, setStats] = useState<Stats | null>(null);
  const [searchInput, setSearchInput] = useState('');
  const [searchFilter, setSearchFilter] = useState('');
  const [groupFilter, setGroupFilter] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [locationFilter, setLocationFilter] = useState<string>('');
  const [showOnlyNew, setShowOnlyNew] = useState(false);
  
  const loadingRef = useRef(false);
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const observerTarget = useRef<HTMLDivElement | null>(null);

  // Load posts
  const loadPosts = useCallback(async (reset: boolean = false) => {
    if (loadingRef.current) return;
    loadingRef.current = true;
    
    if (reset) {
      setOffset(0);
      setPosts([]);
      setLoading(true);
    } else {
      setLoadingMore(true);
    }
    
    setError(null);
    
    try {
      const currentOffset = reset ? 0 : offset;
      const response = await api.getPosts(
        PAGE_SIZE,
        currentOffset,
        groupFilter || undefined,
        searchFilter || undefined,
        showOnlyNew,
        categoryFilter || undefined,
        locationFilter || undefined
      );
      
      if (reset) {
        setPosts(response.posts);
        setOffset(response.posts.length);
      } else {
        setPosts(prev => [...prev, ...response.posts]);
        setOffset(prev => prev + response.posts.length);
      }
      
      setTotal(response.total);
      setHasMore(response.posts.length >= PAGE_SIZE && (reset ? response.posts.length : offset + response.posts.length) < response.total);
    } catch (err: any) {
      setError(err.message || 'Failed to load posts');
    } finally {
      setLoading(false);
      setLoadingMore(false);
      loadingRef.current = false;
    }
  }, [offset, groupFilter, searchFilter, showOnlyNew]);

  // Load stats
  const loadStats = useCallback(async () => {
    try {
      const statsData = await api.getStats();
      setStats(statsData);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadPosts(true);
    loadStats();
  }, []);

  // Reload when filters change
  useEffect(() => {
    loadPosts(true);
  }, [groupFilter, searchFilter, showOnlyNew, categoryFilter, locationFilter]);

  // Auto-refresh every 2 minutes to sync with monitoring cycles
  useEffect(() => {
    const AUTO_REFRESH_INTERVAL = 120000; // 2 minutes (120000ms)
    
    console.log('Auto-refresh enabled: Dashboard will refresh every 2 minutes');
    
    const intervalId = setInterval(() => {
      console.log('Auto-refreshing dashboard...');
      loadPosts(true);
      loadStats();
    }, AUTO_REFRESH_INTERVAL);

    // Cleanup interval on component unmount
    return () => {
      console.log('Auto-refresh disabled');
      clearInterval(intervalId);
    };
  }, [groupFilter, searchFilter, showOnlyNew, categoryFilter, locationFilter]);

  // Debounced search
  const handleSearchChange = (value: string) => {
    setSearchInput(value);
    
    if (searchDebounceRef.current) {
      clearTimeout(searchDebounceRef.current);
    }
    
    searchDebounceRef.current = setTimeout(() => {
      setSearchFilter(value);
    }, 300);
  };

  // Infinite scroll observer
  useEffect(() => {
    if (!hasMore || loading || loadingMore) return;
    
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !loading && !loadingMore && hasMore) {
          loadPosts(false);
        }
      },
      { rootMargin: '300px', threshold: 0.01 }
    );

    const currentTarget = observerTarget.current;
    if (currentTarget) {
      observer.observe(currentTarget);
    }

    return () => {
      if (currentTarget) {
        observer.unobserve(currentTarget);
      }
    };
  }, [loading, loadingMore, hasMore, loadPosts]);

  // Format scraped_at date
  const formatDate = (isoString: string): string => {
    try {
      const date = new Date(isoString);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return isoString;
    }
  };

  // Get unique groups, categories, and locations for filter dropdowns
  const uniqueGroups = stats?.by_group.map(g => ({ name: g.group, url: '' })) || [];
  
  // Get unique categories from posts
  const uniqueCategories = Array.from(new Set(posts.map(p => p.category).filter(Boolean)));
  
  // Get unique locations from posts
  const uniqueLocations = Array.from(new Set(posts.map(p => p.location).filter(Boolean)));

  // Get category display with icon (fallback for non-AI processed posts)
  const getCategoryDisplay = (post: Post) => {
    if (post.category) {
      // Use AI-extracted category
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
    
    // Fallback: keyword-based categorization for old posts
    const content = (post.title + ' ' + post.text).toLowerCase();
    if (content.match(/(flytte|bære|transport|frakte|hente|kjøre|bil|henger)/)) return { icon: '🚚', name: 'Transport / Moving' };
    if (content.match(/(male|sparkle|pusse|oppussing|renovere|snekker|gulv|vegg)/)) return { icon: '🎨', name: 'Painting / Renovation' };
    if (content.match(/(vask|rengjøring|utvask|hage|klippe|måke|snø)/)) return { icon: '🧹', name: 'Cleaning / Garden' };
    if (content.match(/(rørlegger|elektriker|strøm|vann|vvs|lys)/)) return { icon: '🔧', name: 'Plumbing / Electrical' };
    if (content.match(/(montere|demontere|ikea|møbler|skap|seng|sofa)/)) return { icon: '🪑', name: 'Assembly / Furniture' };
    
    return { icon: '📦', name: 'General' };
  };

  return (
    <div className="container">
      <div className="header">
        <h1>🚗 Facebook Work Notifier Dashboard</h1>
        <div className="stats-bar">
          <div className="stat-item">
            <span className="stat-label">Total Posts:</span>
            <span className="stat-value">{stats?.total || 0}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">New Posts:</span>
            <span className="stat-value highlight">{stats?.new || 0}</span>
          </div>
          {stats?.by_group.map(group => (
            <div key={group.group} className="stat-item">
              <span className="stat-label">{group.group}:</span>
              <span className="stat-value">{group.count}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="filters">
        <div className="filter-group">
          <label>Search</label>
          <input
            type="text"
            placeholder="Search posts..."
            value={searchInput}
            onChange={(e) => handleSearchChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                if (searchDebounceRef.current) {
                  clearTimeout(searchDebounceRef.current);
                }
                setSearchFilter(searchInput);
              }
            }}
          />
        </div>
        
        <div className="filter-group">
          <label>Group</label>
          <select
            value={groupFilter}
            onChange={(e) => setGroupFilter(e.target.value)}
          >
            <option value="">All Groups</option>
            {uniqueGroups.map(group => (
              <option key={group.name} value={group.name}>{group.name}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Category</label>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
          >
            <option value="">All Categories</option>
            {uniqueCategories.map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Location</label>
          <select
            value={locationFilter}
            onChange={(e) => setLocationFilter(e.target.value)}
          >
            <option value="">All Locations</option>
            {uniqueLocations.map(loc => (
              <option key={loc} value={loc}>{loc}</option>
            ))}
          </select>
        </div>
        
        <div className="filter-group checkbox">
          <label>
            <input
              type="checkbox"
              checked={showOnlyNew}
              onChange={(e) => setShowOnlyNew(e.target.checked)}
            />
            <span>Show only new posts</span>
          </label>
        </div>
        
        <button
          onClick={() => {
            loadStats();
            loadPosts(true);
          }}
          className="refresh-button"
        >
          🔄 Refresh
        </button>
      </div>

      {error && <div className="error">Error: {error}</div>}

      {loading ? (
        <div className="loading">Loading posts...</div>
      ) : posts.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📭</div>
          <h2>No Posts Found</h2>
          <p>No posts match your current filters. Try adjusting your search or filters.</p>
        </div>
      ) : (
        <>
          <div className="posts-grid">
            {posts.map((post) => (
              <div 
                key={post.post_id} 
                className="post-card clickable"
                onClick={() => navigate(`/post/${encodeURIComponent(post.post_id)}`)}
              >
                {/* Posted Date - Most Important */}
                <div className="post-date">
                  🕒 {post.timestamp}
                </div>

                {/* Category Tag - Right after date */}
                <div className="category-tag">
                  {(() => {
                    const cat = getCategoryDisplay(post);
                    return (
                      <span className="category-badge">
                        {cat.icon} {cat.name}
                      </span>
                    );
                  })()}
                </div>

                {/* Location Tag */}
                {post.location && (
                  <div className="location-tag">
                    <span className="location-badge">
                      📍 {post.location}
                    </span>
                  </div>
                )}

                <div className="post-header">
                  <h3 className="post-title">{post.title}</h3>

                  {post.notified === 1 && (
                    <span className="notified-badge">✅ Notified</span>
                  )}
                </div>
                
                <div className="post-meta">
                  <div className="post-meta-item">
                    <span className="meta-label">🆔 Post ID:</span>
                    <span className="meta-value">{post.post_id}</span>
                  </div>
                  <div className="post-meta-item">
                    <span className="meta-label">📅 Scraped:</span>
                    <span className="meta-value">{formatDate(post.scraped_at)}</span>
                  </div>
                  <div className="post-meta-item">
                    <span className="meta-label">📍 Group:</span>
                    <span className="group-link">{post.group_name}</span>
                  </div>
                </div>
                
                <div className="post-text">
                  {post.text.length > 150 ? post.text.substring(0, 150) + '...' : post.text}
                </div>
                
                <div className="view-details-hint">
                  Click to view details →
                </div>
              </div>
            ))}
          </div>
          
          {/* Sentinel for infinite scroll */}
          {hasMore && (
            <div ref={observerTarget} style={{ height: '100px', opacity: 0 }} aria-hidden="true" />
          )}
          
          {loadingMore && (
            <div className="loading-more">Loading more posts...</div>
          )}
          
          <div className="pagination-info">
            Showing {posts.length} of {total} posts
            {hasMore && ' (scroll for more)'}
          </div>
        </>
      )}
    </div>
  );
}
