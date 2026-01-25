"""API client for Facebook Work Notifier dashboard."""

const API_BASE = '/api';

export interface Post {
  post_id: string;
  title: string;
  text: string;
  url: string;
  timestamp: string;
  group_name: string;
  group_url: string;
  scraped_at: string;
  notified: number;
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
    groupUrl?: string,
    search?: string,
    onlyNew: boolean = false
  ): Promise<PostsResponse> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });
    
    if (groupUrl) params.append('group_url', groupUrl);
    if (search) params.append('search', search);
    if (onlyNew) params.append('only_new', 'true');
    
    const response = await fetch(`${API_BASE}/posts?${params}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch posts: ${response.statusText}`);
    }
    return response.json();
  },
  
  async getStats(): Promise<Stats> {
    const response = await fetch(`${API_BASE}/stats`);
    if (!response.ok) {
      throw new Error(`Failed to fetch stats: ${response.statusText}`);
    }
    return response.json();
  }
};
