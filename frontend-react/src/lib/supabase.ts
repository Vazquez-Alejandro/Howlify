import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || "https://aqzkysgzljxqmckzfpfq.supabase.co";
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFxemt5c2d6bGp4cW1ja3pmcGZxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIxMTU4NTMsImV4cCI6MjA4NzY5MTg1M30.XDqg5IG1ES_4UWAuWxwdGws43siLhYkDZciIRVzr3Lc";

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
