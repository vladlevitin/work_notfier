import type { VercelRequest, VercelResponse } from '@vercel/node';
import { createClient } from '@supabase/supabase-js';

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
) {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', '*');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Initialize Supabase client
    const supabaseUrl = process.env.SUPABASE_URL;
    const supabaseKey = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY;

    if (!supabaseUrl || !supabaseKey) {
      return res.status(500).json({ 
        error: 'Server configuration error',
        details: 'Missing Supabase credentials'
      });
    }

    const supabase = createClient(supabaseUrl, supabaseKey);

    // Parse query parameters
    const limit = Math.min(Math.max(parseInt(req.query.limit as string) || 100, 1), 1000);
    const offset = Math.max(parseInt(req.query.offset as string) || 0, 0);
    const groupUrl = req.query.group_url as string | undefined;
    const search = req.query.search as string | undefined;
    const onlyNew = req.query.only_new === 'true';
    const category = req.query.category as string | undefined;
    const location = req.query.location as string | undefined;

    // Build query for posts
    let query = supabase.from('posts').select('*');

    if (groupUrl) {
      query = query.eq('group_url', groupUrl);
    }

    if (search) {
      query = query.or(`title.ilike.%${search}%,text.ilike.%${search}%`);
    }

    if (onlyNew) {
      query = query.eq('notified', false);
    }

    if (category) {
      query = query.eq('category', category);
    }

    if (location) {
      query = query.ilike('location', `%${location}%`);
    }

    // Sort by posted_at (when the post was originally made on Facebook)
    // Falls back to scraped_at if posted_at is null
    query = query.order('posted_at', { ascending: false, nullsFirst: false });
    query = query.range(offset, offset + limit - 1);

    const { data: posts, error: postsError } = await query;

    if (postsError) throw postsError;

    // Get total count with same filters
    let countQuery = supabase.from('posts').select('*', { count: 'exact', head: true });

    if (groupUrl) {
      countQuery = countQuery.eq('group_url', groupUrl);
    }

    if (search) {
      countQuery = countQuery.or(`title.ilike.%${search}%,text.ilike.%${search}%`);
    }

    if (onlyNew) {
      countQuery = countQuery.eq('notified', false);
    }

    if (category) {
      countQuery = countQuery.eq('category', category);
    }

    if (location) {
      countQuery = countQuery.ilike('location', `%${location}%`);
    }

    const { count, error: countError } = await countQuery;

    if (countError) throw countError;

    return res.status(200).json({
      posts: posts || [],
      total: count || 0,
      limit,
      offset,
    });
  } catch (error: any) {
    console.error('Error fetching posts:', error);
    return res.status(500).json({ 
      error: 'Failed to fetch posts',
      message: error.message 
    });
  }
}
