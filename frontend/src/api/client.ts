// API client for Facebook Work Notifier dashboard

const API_BASE = import.meta.env.VITE_API_URL || '/api';

export interface Post {
  post_id: string;
  title: string;
  text: string;
  url: string;
  timestamp: string;
  posted_at?: string;  // Actual posted time (ISO format)
  group_name: string;
  group_url: string;
  scraped_at: string;
  notified: number;
  category?: string;
  secondary_categories?: string;  // JSON string of secondary category names
  location?: string;
  ai_processed?: boolean;
  // Auto-message fields (transport posts)
  auto_message_sent?: boolean;
  auto_message_text?: string;
  auto_message_price_nok?: number;
  auto_message_hours?: number;
  auto_message_item_summary?: string;
  auto_message_sent_at?: string;
}

export interface PostsResponse {
  posts: Post[];
  total: number;
  limit: number;
  offset: number;
}

export interface Stats {
  total: number;
  new: number;
  by_group: Array<{ group: string; count: number }>;
}

export const api = {
  async getPosts(
    limit: number = 100,
    offset: number = 0,
    groupName?: string,
    search?: string,
    onlyNew: boolean = false,
    category?: string,
    location?: string
  ): Promise<PostsResponse> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });
    
    if (groupName) params.append('group_name', groupName);
    if (search) params.append('search', search);
    if (onlyNew) params.append('only_new', 'true');
    if (category) params.append('category', category);
    if (location) params.append('location', location);
    
    const response = await fetch(`${API_BASE}/posts?${params}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch posts: ${response.statusText}`);
    }
    return response.json();
  },

  async getPostById(postId: string): Promise<Post> {
    const response = await fetch(`${API_BASE}/posts/${encodeURIComponent(postId)}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch post: ${response.statusText}`);
    }
    const data = await response.json();
    return data.post;
  },
  
  async getStats(): Promise<Stats> {
    const response = await fetch(`${API_BASE}/stats`);
    if (!response.ok) {
      throw new Error(`Failed to fetch stats: ${response.statusText}`);
    }
    return response.json();
  }
};
