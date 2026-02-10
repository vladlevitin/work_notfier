import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { api, Post, Stats } from '../api/client';
import './Posts.css';

const MAX_FETCH = 1000;

export function PostsPage() {
  const [allPosts, setAllPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [searchInput, setSearchInput] = useState('');
  const [searchFilter, setSearchFilter] = useState('');
  const [groupFilter, setGroupFilter] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [locationFilter, setLocationFilter] = useState<string>('');
  const [showOnlyNew, setShowOnlyNew] = useState(false);
  
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load all posts from backend (server handles search + onlyNew, everything else client-side)
  const loadPosts = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.getPosts(
        MAX_FETCH,
        0,
        undefined,
        searchFilter || undefined,
        showOnlyNew
      );
      
      setAllPosts(response.posts);
    } catch (err: any) {
      setError(err.message || 'Failed to load posts');
    } finally {
      setLoading(false);
    }
  }, [searchFilter, showOnlyNew]);

  // Normalize group name: strip "(1) ", "(2) " etc. prefixes
  const normalizeGroupName = (name: string): string => {
    return name.replace(/^\(\d+\)\s*/, '');
  };

  // Load stats
  const loadStats = useCallback(async () => {
    try {
      const statsData = await api.getStats();
      
      // Merge groups with same normalized name
      if (statsData.by_group) {
        const merged: Record<string, number> = {};
        for (const g of statsData.by_group) {
          const normalized = normalizeGroupName(g.group);
          merged[normalized] = (merged[normalized] || 0) + g.count;
        }
        statsData.by_group = Object.entries(merged)
          .map(([group, count]) => ({ group, count }))
          .sort((a, b) => b.count - a.count);
      }
      
      setStats(statsData);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadPosts();
    loadStats();
  }, []);

  // Reload when server-side filters change (search, onlyNew)
  useEffect(() => {
    loadPosts();
  }, [searchFilter, showOnlyNew]);

  // Auto-refresh every 2 minutes
  useEffect(() => {
    const intervalId = setInterval(() => {
      loadPosts();
      loadStats();
    }, 120000);
    return () => clearInterval(intervalId);
  }, [searchFilter, showOnlyNew]);

  // Debounced search
  const handleSearchChange = (value: string) => {
    setSearchInput(value);
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    searchDebounceRef.current = setTimeout(() => setSearchFilter(value), 300);
  };

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

  // Format posted_at date (more detailed)
  const formatPostedDate = (isoString: string): string => {
    try {
      const date = new Date(isoString);
      return date.toLocaleString('en-US', {
        weekday: 'short',
        month: 'short',
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
      return formatPostedDate(post.posted_at);
    }
    return post.timestamp;
  };

  // Get unique groups, categories, and locations for filter dropdowns
  const uniqueGroups = stats?.by_group.map(g => ({ name: g.group, url: '' })) || [];
  
  // All predefined categories (matching AI processor categories exactly)
  const allCategories = [
    'Transport / Moving',
    'Manual Labor',
    'Electrical',
    'Plumbing',
    'Painting / Renovation',
    'Cleaning / Garden',
    'Assembly / Furniture',
    'Car Mechanic',
    'Handyman / Misc',
    'IT / Tech',
    'Other'
  ];
  
  // Get unique locations from all posts
  const uniqueLocations = Array.from(new Set(allPosts.map(p => p.location).filter(Boolean)));

  // Get category display with icon — uses AI-assigned category, falls back to keyword matching
  const getCategoryDisplay = (post: Post) => {
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

    // Use AI-assigned category if available
    if (post.category && post.category !== 'Other' && post.category !== 'General') {
      const icon = categoryIcons[post.category] || 
        Object.entries(categoryIcons).find(([key]) => post.category!.includes(key))?.[1] || 
        '📦';
      return { icon, name: post.category };
    }

    // Fallback: keyword-based categorization (same as PostDetail)
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

  // Client-side filtering — all filters combine as AND conditions
  const displayedPosts = useMemo(() => {
    return allPosts.filter((post) => {
      if (groupFilter) {
        const postGroup = normalizeGroupName(post.group_name);
        if (postGroup !== groupFilter) return false;
      }
      if (categoryFilter) {
        const displayedCategory = getCategoryDisplay(post).name;
        if (displayedCategory !== categoryFilter) return false;
      }
      if (locationFilter) {
        if (!post.location || !post.location.toLowerCase().includes(locationFilter.toLowerCase())) return false;
      }
      return true;
    });
  }, [allPosts, groupFilter, categoryFilter, locationFilter]);

  return (
    <div className="container">
      <div className="header">
        <h1>🚗 Facebook Work Notifier Dashboard</h1>
        
        {/* Dynamic Post Count */}
        <div className="stats-bar stats-aggregate">
          <div className="stat-item stat-large">
            <span className="stat-label">
              {(groupFilter || categoryFilter || locationFilter || searchFilter || showOnlyNew) ? 'Matching Posts' : 'Total Posts'}
            </span>
            <span className="stat-value">{displayedPosts.length}</span>
          </div>
        </div>
        
        {/* Per-Group Stats Section — dynamically reflects all filters */}
        {(() => {
          const hasFilters = groupFilter || categoryFilter || locationFilter || searchFilter || showOnlyNew;
          const groupData = hasFilters
            ? Object.entries(
                displayedPosts.reduce<Record<string, number>>((acc, p) => {
                  const name = normalizeGroupName(p.group_name);
                  acc[name] = (acc[name] || 0) + 1;
                  return acc;
                }, {})
              )
                .map(([group, count]) => ({ group, count }))
                .sort((a, b) => b.count - a.count)
            : stats?.by_group || [];

          return groupData.length > 0 ? (
            <div className="stats-bar stats-groups">
              <div className="stats-groups-header">Posts by Group</div>
              <div className="stats-groups-grid">
                {groupData.map(group => (
                  <div key={group.group} className="stat-item-group">
                    <span className="stat-group-name">{group.group}</span>
                    <span className="stat-group-count">{group.count}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : null;
        })()}
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
            {allCategories.map(cat => (
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
            loadPosts();
          }}
          className="refresh-button"
        >
          🔄 Refresh
        </button>
      </div>

      {error && <div className="error">Error: {error}</div>}

      {loading ? (
        <div className="loading">Loading posts...</div>
      ) : displayedPosts.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📭</div>
          <h2>No Posts Found</h2>
          <p>No posts match your current filters. Try adjusting your search or filters.</p>
        </div>
      ) : (
        <>
          <div className="posts-grid">
            {displayedPosts.map((post) => (
              <a 
                key={post.post_id} 
                href={`/post/${encodeURIComponent(post.post_id)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="post-card clickable"
              >
                {/* Posted Date - Most Important */}
                <div className="post-date">
                  🕒 {getDisplayTimestamp(post)}
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
                    <span className="group-link">{normalizeGroupName(post.group_name)}</span>
                  </div>
                </div>
                
                <div className="post-text">
                  {post.text.length > 80 ? post.text.substring(0, 80) + '...' : post.text}
                </div>
                
                <div className="view-details-hint">
                  Click to view details →
                </div>
              </a>
            ))}
          </div>
          
          <div className="pagination-info">
            Showing {displayedPosts.length} posts
          </div>
        </>
      )}
    </div>
  );
}
