"""Sample mentions for local development and dashboard demos.
NOT real social posts — synthesized from common RTA feedback patterns."""
from datetime import datetime, timezone, timedelta

now = datetime.now(timezone.utc)
ago = lambda m: (now - timedelta(minutes=m)).isoformat()

SAMPLE_MENTIONS = [
    {
        "id": "reddit:demo01", "platform": "reddit", "native_id": "demo01",
        "url": "https://www.reddit.com/r/dubai/comments/demo01",
        "author_handle": "u/commuter_jbr", "author_followers": 0,
        "text": "Bus 50 was 25 minutes late again this morning, third time this week. RTA needs to look at the schedule.",
        "created_at": ago(8), "fetched_at": now.isoformat(),
        "likes": 47, "shares": 3, "replies": 12, "reach_estimate": 350000,
    },
    {
        "id": "reddit:demo02", "platform": "reddit", "native_id": "demo02",
        "url": "https://www.reddit.com/r/dubai/comments/demo02",
        "author_handle": "u/marina_resident", "author_followers": 0,
        "text": "Hala taxi driver was professional and the ride was smooth. Thanks RTA.",
        "created_at": ago(22), "fetched_at": now.isoformat(),
        "likes": 89, "shares": 1, "replies": 4, "reach_estimate": 350000,
    },
    {
        "id": "x:demo03", "platform": "x", "native_id": "demo03",
        "url": "https://x.com/i/status/demo03",
        "author_handle": "@dubai_traveler", "author_followers": 18400, "author_verified": False,
        "text": "Taxi driver refused to take me to Al Quoz from DIFC. Reported to RTA. This shouldn't be happening.",
        "created_at": ago(15), "fetched_at": now.isoformat(),
        "likes": 142, "shares": 38, "replies": 21, "reach_estimate": 18400,
    },
    {
        "id": "x:demo04", "platform": "x", "native_id": "demo04",
        "url": "https://x.com/i/status/demo04",
        "author_handle": "@accessibility_uae", "author_followers": 9200, "author_verified": True,
        "text": "Wheelchair ramp at Al Ghubaiba marine station broken for 4 days now. @rta_dubai please fix urgently.",
        "created_at": ago(35), "fetched_at": now.isoformat(),
        "likes": 312, "shares": 89, "replies": 47, "reach_estimate": 9200,
    },
    {
        "id": "news_rss:demo05", "platform": "news_rss", "native_id": "demo05",
        "url": "https://www.khaleejtimes.com/transport/example",
        "author_handle": "Khaleej Times", "author_followers": 0,
        "text": "RTA Dubai launches new feeder bus routes connecting metro stations to major residential areas — community welcomes the move.",
        "created_at": ago(120), "fetched_at": now.isoformat(),
        "likes": 0, "shares": 0, "replies": 0, "reach_estimate": 80000,
    },
    {
        "id": "x:demo06", "platform": "x", "native_id": "demo06",
        "url": "https://x.com/i/status/demo06",
        "author_handle": "@daily_metro_user", "author_followers": 2100, "author_verified": False,
        "text": "تأخير حافلة الخط 24 من ميناء راشد. الحرارة ٤٢ درجة والانتظار ٢٠ دقيقة. شكوى رسمية.",
        "language": "ar",
        "created_at": ago(11), "fetched_at": now.isoformat(),
        "likes": 64, "shares": 12, "replies": 8, "reach_estimate": 2100,
    },
    {
        "id": "reddit:demo07", "platform": "reddit", "native_id": "demo07",
        "url": "https://www.reddit.com/r/uae/comments/demo07",
        "author_handle": "u/student_aus", "author_followers": 0,
        "text": "nol card top-up not reflecting on the app. Anyone else? Have a class in 30 min.",
        "created_at": ago(6), "fetched_at": now.isoformat(),
        "likes": 23, "shares": 0, "replies": 17, "reach_estimate": 120000,
    },
    {
        "id": "x:demo08", "platform": "x", "native_id": "demo08",
        "url": "https://x.com/i/status/demo08",
        "author_handle": "@uae_traveler", "author_followers": 45200, "author_verified": False,
        "text": "Abra crossing the creek at sunset — best 1 dirham you'll ever spend in Dubai. Thanks RTA marine team.",
        "created_at": ago(180), "fetched_at": now.isoformat(),
        "likes": 1240, "shares": 188, "replies": 92, "reach_estimate": 45200,
    },
    {
        "id": "x:demo09", "platform": "x", "native_id": "demo09",
        "url": "https://x.com/i/status/demo09",
        "author_handle": "@expat_dxb", "author_followers": 6700, "author_verified": False,
        "text": "Reckless driving by airport taxi from Terminal 3, swerving across lanes. Plate noted, complaint filed.",
        "created_at": ago(42), "fetched_at": now.isoformat(),
        "likes": 198, "shares": 34, "replies": 15, "reach_estimate": 6700,
    },
    {
        "id": "facebook:demo10", "platform": "facebook", "native_id": "demo10",
        "url": "https://facebook.com/rta.dubai/posts/demo10",
        "author_handle": "Sara M.", "author_followers": 0,
        "text": "Customer service at Al Karama Customer Happiness Centre was excellent today. Issue resolved in under 15 minutes. Appreciate it.",
        "created_at": ago(95), "fetched_at": now.isoformat(),
        "likes": 56, "shares": 0, "replies": 3, "reach_estimate": 0,
    },
    {
        "id": "reddit:demo11", "platform": "reddit", "native_id": "demo11",
        "url": "https://www.reddit.com/r/dubai/comments/demo11",
        "author_handle": "u/business_bay_local", "author_followers": 0,
        "text": "Driver of bus X25 refused to stop at the requested stop, kept going. Filthy AC dripping on passengers. Filed RTA complaint.",
        "created_at": ago(18), "fetched_at": now.isoformat(),
        "likes": 71, "shares": 4, "replies": 19, "reach_estimate": 350000,
    },
    {
        "id": "x:demo12", "platform": "x", "native_id": "demo12",
        "url": "https://x.com/i/status/demo12",
        "author_handle": "@dxb_resident", "author_followers": 1100, "author_verified": False,
        "text": "Why is Hala taxi surge pricing 3x normal at 11pm on a Tuesday? Make this fair, RTA.",
        "created_at": ago(4), "fetched_at": now.isoformat(),
        "likes": 87, "shares": 19, "replies": 32, "reach_estimate": 1100,
    },
]
