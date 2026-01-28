import type { VercelRequest, VercelResponse } from '@vercel/node';
import { createClient } from '@supabase/supabase-js';

// Parse Facebook timestamp strings into Date objects
function parseFacebookTimestamp(timestamp: string): Date {
  const now = new Date();
  
  // Handle "Xh" format (X hours ago)
  const hoursMatch = timestamp.match(/^(\d+)h$/);
  if (hoursMatch) {
    const hours = parseInt(hoursMatch[1]);
    return new Date(now.getTime() - hours * 60 * 60 * 1000);
  }
  
  // Handle "Xd" format (X days ago)
  const daysMatch = timestamp.match(/^(\d+)d$/);
  if (daysMatch) {
    const days = parseInt(daysMatch[1]);
    return new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
  }
  
  // Handle "DD Month at HH:MM" format (e.g., "24 January at 08:42")
  const dateMatch = timestamp.match(/^(\d+)\s+(\w+)\s+at\s+(\d+):(\d+)$/);
  if (dateMatch) {
    const day = parseInt(dateMatch[1]);
    const month = dateMatch[2];
    const hour = parseInt(dateMatch[3]);
    const minute = parseInt(dateMatch[4]);
    
    const monthMap: { [key: string]: number } = {
      'January': 0, 'February': 1, 'March': 2, 'April': 3,
      'May': 4, 'June': 5, 'July': 6, 'August': 7,
      'September': 8, 'October': 9, 'November': 10, 'December': 11
    };
    
    const monthIndex = monthMap[month];
    if (monthIndex !== undefined) {
      const year = now.getFullYear();
      const date = new Date(year, monthIndex, day, hour, minute);
      
      // If date is in the future, it's probably from last year
      if (date > now) {
        date.setFullYear(year - 1);
      }
      
      return date;
    }
  }
  
  // Handle "Recently" or unknown formats - return current time
  return now;
}

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

    // Fetch ALL posts (without pagination) so we can sort them properly
    // Then apply pagination manually after sorting
    const { data: allPosts, error: postsError } = await query;

    if (postsError) throw postsError;

    // Sort ALL posts by parsed timestamp (most recent first)
    const sortedAllPosts = (allPosts || []).sort((a, b) => {
      const dateA = parseFacebookTimestamp(a.timestamp || '');
      const dateB = parseFacebookTimestamp(b.timestamp || '');
      return dateB.getTime() - dateA.getTime(); // Descending order (newest first)
    });

    // Apply pagination AFTER sorting
    const sortedPosts = sortedAllPosts.slice(offset, offset + limit);

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
      posts: sortedPosts,
      total: sortedAllPosts.length, // Use actual sorted length, not DB count
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
