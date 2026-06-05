-- database/queries/engagement_analytics.sql
-- Extracts digital engagement streams and channel usage metrics for customer opportunity scoring.

-- Query 1: Chronological click and open events to feed Python EWMA engine.
-- Click events are weighted 2; email open events are weighted 1.
SELECT
    customer_id,
    offer_category,
    channel,
    'click' AS event_type,
    clicked_at AS event_time,
    2 AS event_value
FROM campaign_clicks
UNION ALL
SELECT
    customer_id,
    offer_category,
    'email' AS channel,
    'open' AS event_type,
    opened_at AS event_time,
    1 AS event_value
FROM email_opens
ORDER BY customer_id, event_time ASC;

-- Query 2: Distinct channels used by each customer in the last 30 days.
-- Used to calculate the channel diversity multiplier (cap at 3 channels).
SELECT
    customer_id,
    COUNT(DISTINCT channel) AS distinct_channels_30d
FROM (
    SELECT customer_id, channel, clicked_at AS event_time FROM campaign_clicks WHERE clicked_at >= DATE_SUB('2026-06-05', INTERVAL 30 DAY)
    UNION ALL
    SELECT customer_id, 'email' AS channel, opened_at AS event_time FROM email_opens WHERE opened_at >= DATE_SUB('2026-06-05', INTERVAL 30 DAY)
) AS combined_engagement
GROUP BY customer_id;
