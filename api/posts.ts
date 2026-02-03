import type { VercelRequest, VercelResponse } from '@vercel/node';
import { createClient } from '@supabase/supabase-js';

// Parse Facebook timestamp strings into Date objects
function parseFacebookTimestamp(timestamp: string): Date {
  const now = new Date();
  
  const monthMap: { [key: string]: number } = {
    'January': 0, 'February': 1, 'March': 2, 'April': 3,
    'May': 4, 'June': 5, 'July': 6, 'August': 7,
    'September': 8, 'October': 9, 'November': 10, 'December': 11
  };
  
  // Handle full format with day name: "Sunday 1 February 2026 at 14:08"
  const fullDateMatch = timestamp.match(/^(?:Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)\s+(\d+)\s+(\w+)\s+(\d{4})\s+at\s+(\d+):(\d+)$/i);
  if (fullDateMatch) {
    const day = parseInt(fullDateMatch[1]);
    const month = fullDateMatch[2];
    const year = parseInt(fullDateMatch[3]);
    const hour = parseInt(fullDateMatch[4]);
    const minute = parseInt(fullDateMatch[5]);
    
    const monthIndex = monthMap[month];
    if (monthIndex !== undefined) {
      return new Date(year, monthIndex, day, hour, minute);
    }
  }
  
  // Handle "Xm" format (X minutes ago)
  const minutesMatch = timestamp.match(/^(\d+)m$/);
  if (minutesMatch) {
    const minutes = parseInt(minutesMatch[1]);
    return new Date(now.getTime() - minutes * 60 * 1000);
  }
  
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
  
  // Handle "Yesterday at HH:MM" format
  const yesterdayMatch = timestamp.match(/^Yesterday\s+at\s+(\d+):(\d+)$/);
  if (yesterdayMatch) {
    const hour = parseInt(yesterdayMatch[1]);
    const minute = parseInt(yesterdayMatch[2]);
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    yesterday.setHours(hour, minute, 0, 0);
    return yesterday;
  }
  
  // Handle "DD Month at HH:MM" format (e.g., "24 January at 08:42")
  const dateTimeMatch = timestamp.match(/^(\d+)\s+(\w+)\s+at\s+(\d+):(\d+)$/);
  if (dateTimeMatch) {
    const day = parseInt(dateTimeMatch[1]);
    const month = dateTimeMatch[2];
    const hour = parseInt(dateTimeMatch[3]);
    const minute = parseInt(dateTimeMatch[4]);
    
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
  
  // Handle "DD Month YYYY at HH:MM" format (e.g., "5 May 2025 at 14:30")
  const dateYearTimeMatch = timestamp.match(/^(\d+)\s+(\w+)\s+(\d{4})\s+at\s+(\d+):(\d+)$/);
  if (dateYearTimeMatch) {
    const day = parseInt(dateYearTimeMatch[1]);
    const month = dateYearTimeMatch[2];
    const year = parseInt(dateYearTimeMatch[3]);
    const hour = parseInt(dateYearTimeMatch[4]);
    const minute = parseInt(dateYearTimeMatch[5]);
    
    const monthIndex = monthMap[month];
    if (monthIndex !== undefined) {
      return new Date(year, monthIndex, day, hour, minute);
    }
  }
  
  // Handle "DD Month YYYY" format (e.g., "5 May 2025")
  const dateYearMatch = timestamp.match(/^(\d+)\s+(\w+)\s+(\d{4})$/);
  if (dateYearMatch) {
    const day = parseInt(dateYearMatch[1]);
    const month = dateYearMatch[2];
    const year = parseInt(dateYearMatch[3]);
    
    const monthIndex = monthMap[month];
    if (monthIndex !== undefined) {
      return new Date(year, monthIndex, day, 12, 0); // Default to noon
    }
  }
  
  // Handle "Recently" - treat as very recent (1 minute ago)
  if (timestamp.toLowerCase() === 'recently') {
    return new Date(now.getTime() - 60 * 1000);
  }
  
  // Unknown formats - return a very old date so they sort to the bottom
  return new Date(0);
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
      // Match by group name (the filter sends group name, not URL)
      query = query.ilike('group_name', `%${groupUrl}%`);
    }

    if (search) {
      query = query.or(`title.ilike.%${search}%,text.ilike.%${search}%`);
    }

    if (onlyNew) {
      query = query.eq('notified', false);
    }

    if (location) {
      query = query.ilike('location', `%${location}%`);
    }

    // Fetch ALL posts (without pagination) so we can sort them properly
    // Then apply pagination manually after sorting
    const { data: allPosts, error: postsError } = await query;

    if (postsError) throw postsError;

    // Filter by category client-side (to avoid Supabase query issues with special chars)
    let filteredPosts = allPosts || [];
    if (category) {
      const categoryLower = category.toLowerCase();
      filteredPosts = filteredPosts.filter(post => 
        post.category && post.category.toLowerCase().includes(categoryLower)
      );
    }

    // Sort ALL posts by parsed timestamp (most recent first)
    const sortedAllPosts = filteredPosts.sort((a, b) => {
      const dateA = parseFacebookTimestamp(a.timestamp || '');
      const dateB = parseFacebookTimestamp(b.timestamp || '');
      return dateB.getTime() - dateA.getTime(); // Descending order (newest first)
    });

    // Apply pagination AFTER sorting
    const sortedPosts = sortedAllPosts.slice(offset, offset + limit);

    // Get total count with same filters
    let countQuery = supabase.from('posts').select('*', { count: 'exact', head: true });

    if (groupUrl) {
      countQuery = countQuery.ilike('group_name', `%${groupUrl}%`);
    }

    if (search) {
      countQuery = countQuery.or(`title.ilike.%${search}%,text.ilike.%${search}%`);
    }

    if (onlyNew) {
      countQuery = countQuery.eq('notified', false);
    }

    if (location) {
      countQuery = countQuery.ilike('location', `%${location}%`);
    }

    // Note: category filtering is done client-side, so total uses filteredPosts length
    return res.status(200).json({
      posts: sortedPosts,
      total: sortedAllPosts.length,
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
