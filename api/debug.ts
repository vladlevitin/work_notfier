import type { VercelRequest, VercelResponse } from '@vercel/node';

export default function handler(req: VercelRequest, res: VercelResponse) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', '*');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const envKeys = Object.keys(process.env || {});
  const supabaseKeys = envKeys.filter((key) => key.includes('SUPABASE'));

  return res.status(200).json({
    hasSupabaseUrl: Boolean(process.env.SUPABASE_URL),
    hasSupabaseKey: Boolean(process.env.SUPABASE_KEY),
    hasSupabaseServiceKey: Boolean(process.env.SUPABASE_SERVICE_KEY),
    supabaseKeys,
    envKeyCount: envKeys.length,
  });
}
