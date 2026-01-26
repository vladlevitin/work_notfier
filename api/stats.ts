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

    // Get total posts
    const { count: total, error: totalError } = await supabase
      .from('posts')
      .select('*', { count: 'exact', head: true });

    if (totalError) throw totalError;

    // Get new posts (not notified)
    const { count: newPosts, error: newError } = await supabase
      .from('posts')
      .select('*', { count: 'exact', head: true })
      .eq('notified', false);

    if (newError) throw newError;

    // Get posts by group
    const { data: allPosts, error: postsError } = await supabase
      .from('posts')
      .select('group_name');

    if (postsError) throw postsError;

    // Group posts by group_name
    const groupCounts: Record<string, number> = {};
    allPosts?.forEach((post) => {
      const groupName = post.group_name || 'Unknown';
      groupCounts[groupName] = (groupCounts[groupName] || 0) + 1;
    });

    const byGroup = Object.entries(groupCounts)
      .map(([group, count]) => ({ group, count }))
      .sort((a, b) => b.count - a.count);

    return res.status(200).json({
      total: total || 0,
      new: newPosts || 0,
      by_group: byGroup,
    });
  } catch (error: any) {
    console.error('Error fetching stats:', error);
    return res.status(500).json({ 
      error: 'Failed to fetch stats',
      message: error.message 
    });
  }
}
