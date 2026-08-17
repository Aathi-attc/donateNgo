-- ============================================================
-- donateNgo — MySQL backend database
-- Schema + seed data for the donateNgo website.
-- Local server: 127.0.0.1:3306, database: NGODatabase
-- (For LAN sharing: every machine just points at this server;
--  see the "LAN setup" section at the bottom.)
-- ============================================================

CREATE DATABASE IF NOT EXISTS NGODatabase
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE NGODatabase;

-- ---------- Drop order respects the foreign keys ----------
DROP TABLE IF EXISTS donations;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS ngos;

-- ---------- NGOs ----------
CREATE TABLE ngos (
  id          INT PRIMARY KEY AUTO_INCREMENT,
  name        VARCHAR(150)  NOT NULL,
  tagline     VARCHAR(150),
  category    VARCHAR(60)   NOT NULL,
  location    VARCHAR(255)  NOT NULL,
  founded     INT,
  verified    TINYINT       DEFAULT 0,
  description TEXT,
  email       VARCHAR(150),
  phone       VARCHAR(60),
  website     VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------- Users (passwords stored as SHA-256 hashes) ----------
CREATE TABLE users (
  id            INT PRIMARY KEY AUTO_INCREMENT,
  name          VARCHAR(150) NOT NULL,
  email         VARCHAR(190) NOT NULL UNIQUE,
  password_hash VARCHAR(128) NOT NULL,
  location      VARCHAR(255),
  causes        TEXT,
  avatar_color  INT DEFAULT 0,
  avatar_image  LONGTEXT,
  since         INT,
  created_at    DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------- Reviews ----------
CREATE TABLE reviews (
  id         INT PRIMARY KEY AUTO_INCREMENT,
  ngo_id     INT NOT NULL,
  user_id    INT,
  user_name  VARCHAR(150) NOT NULL,
  rating     INT NOT NULL,
  text       TEXT NOT NULL,
  created_at DATETIME,
  CONSTRAINT fk_rev_ngo  FOREIGN KEY (ngo_id)  REFERENCES ngos(id),
  CONSTRAINT fk_rev_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------- Donations (simulated in-app) ----------
CREATE TABLE donations (
  id          INT PRIMARY KEY AUTO_INCREMENT,
  user_id     INT NOT NULL,
  ngo_id      INT NOT NULL,
  amount      DECIMAL(10,2) NOT NULL,
  card_last4  VARCHAR(4),
  status      VARCHAR(64),
  created_at  DATETIME,
  CONSTRAINT fk_don_user FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_don_ngo  FOREIGN KEY (ngo_id)  REFERENCES ngos(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- SEED DATA — 13 real NGOs
-- (NGO details from the NGO INFORMATION.txt handout)
-- ============================================================

INSERT INTO ngos (id, name, tagline, category, location, founded, verified, description, email, phone, website) VALUES
(1, 'The Akshaya Patra Foundation', 'Nutritious mid-day meals for every school child', 'Health & Nutrition', 'Bengaluru, Karnataka', 2000, 1,
 'One of India''s largest NGOs providing nutritious mid-day meals to government school children under the PM POSHAN programme. It also supports disaster relief and food assistance during emergencies. Address: #72, 3rd Floor, 3rd Main Road, Yeshwanthpur Industrial Suburb, Rajajinagar, Bengaluru, Karnataka - 560022',
 'info@akshayapatra.org', '+91 80 4960 7200', 'https://www.akshayapatra.org'),
(2, 'Smile Foundation', 'Community-led development across India', 'Education & Child Welfare', 'New Delhi', 2002, 1,
 'A national NGO working to improve education, healthcare, women empowerment, skill development, and livelihood opportunities through community-based development programmes. Address: 161 B/4, Community Centre, Yusuf Sarai, New Delhi - 110049',
 'info@smilefoundationindia.org', '+91 11 43123700', 'https://www.smilefoundationindia.org'),
(3, 'CRY (Child Rights and You)', 'Every child has the right to a happy childhood', 'Education & Child Welfare', 'Mumbai, Maharashtra', 1979, 1,
 'Works to ensure every child has access to education, healthcare, protection, and equal opportunities by partnering with grassroots organizations across India. Address: 189/A Anand Estate, Sane Guruji Marg, Mumbai, Maharashtra - 400011',
 'info@cry.org', '+91 91159 11500', 'https://www.cry.org'),
(4, 'Goonj', 'Urban surplus, rural progress', 'Community Giving & Relief', 'New Delhi', 1999, 1,
 'Transforms urban surplus into resources for rural communities through clothing drives, sanitation initiatives, livelihood programmes, and disaster relief operations. Address: Bengaluru Collection Centre, Kudlu Gate, Begur, Bengaluru, Karnataka - 560068',
 'info@goonj.org', '+91 82879 69730', 'https://goonj.org'),
(5, 'Pratham Education Foundation', 'Foundational literacy & numeracy for all', 'Education & Child Welfare', 'New Delhi', 1995, 1,
 'One of India''s largest education NGOs, dedicated to improving foundational literacy and numeracy through community learning programmes, teacher training, and the ASER (Annual Status of Education Report) survey. Address: B4 Block, Safdarjung Enclave, New Delhi - 110029',
 'info@pratham.org', '+91 11 41651638', 'https://www.pratham.org'),
(6, 'GiveIndia', 'Giving made simple, transparent & trusted', 'Community Giving & Relief', 'Bengaluru, Karnataka', 2000, 1,
 'India''s largest donation platform connecting donors with verified NGOs across the country. It supports causes such as education, healthcare, child welfare, disaster relief, elderly care, and rural development through transparent fundraising initiatives. Address: GiveIndia Headquarters, Bengaluru, Karnataka',
 'hello@giveindia.org', '+91 22 6170 5700', 'https://www.giveindia.org'),
(7, 'HelpAge India', 'Dignified care for senior citizens', 'Elderly Care', 'New Delhi', 1978, 1,
 'A leading non-profit organization dedicated to improving the lives of disadvantaged senior citizens through healthcare services, livelihood support, advocacy, emergency relief, and awareness programmes across India. Address: C-14, Qutab Institutional Area, New Delhi - 110016',
 'info@helpageindia.org', '+91 11 41688989', 'https://www.helpageindia.org'),
(8, 'Teach For India', 'Fellows teaching for an equal India', 'Education & Child Welfare', 'Mumbai, Maharashtra', 2009, 1,
 'Works to eliminate educational inequality by recruiting outstanding graduates and professionals to teach in under-resourced schools while developing future leaders committed to improving India''s education system. Address: Teach For India Headquarters, Mumbai, Maharashtra - 400013',
 'info@teachforindia.org', '+91 22 67476666', 'https://www.teachforindia.org'),
(9, 'WWF-India', 'Conserving nature for a living planet', 'Environment & Wildlife', 'New Delhi', 1969, 1,
 'One of India''s leading environmental organizations working to conserve wildlife, forests, freshwater ecosystems, biodiversity, and combat climate change through research, education, and community participation. Address: 172-B, Lodi Estate, New Delhi - 110003',
 'info@wwfindia.org', '+91 11 41504777', 'https://www.wwfindia.org'),
(10, 'Magic Bus India Foundation', 'From childhood to livelihood', 'Education & Child Welfare', 'Mumbai, Maharashtra', 1999, 1,
 'Empowers children and young people from underserved communities through education, life-skills training, employability programmes, and career support, helping them move out of poverty. Address: Magic Bus India Foundation, Mumbai, Maharashtra - 400051',
 'info@magicbus.org', '+91 22 68251000', 'https://www.magicbus.org'),
(11, 'Nanhi Kali', 'Educating the girl child', 'Education & Child Welfare', 'Mumbai, Maharashtra', 1996, 1,
 'A non-profit initiative focused on providing quality education and academic support to underprivileged girls across India. It offers educational material, after-school support, and mentorship to help girls complete their schooling. Address: K. C. Mahindra Education Trust, Cecil Court, Mahatma Gandhi Road, Mumbai, Maharashtra - 400001',
 'info@nanhikali.org', '+91 22 22895554', 'https://www.nanhikali.org'),
(12, 'Sightsavers India', 'Eliminating avoidable blindness', 'Health & Nutrition', 'New Delhi', 1966, 1,
 'An international development organization working in India to eliminate avoidable blindness and promote equal opportunities for people with visual impairments and other disabilities through healthcare, education, and livelihood programmes. Address: B-94, Okhla Industrial Area, Phase II, New Delhi - 110020',
 'info@sightsaversindia.org', '+91 11 4653 8000', 'https://www.sightsaversindia.org'),
(13, 'The Leprosy Mission Trust India', 'Working to end leprosy and its impact', 'Health & Nutrition', 'New Delhi', 1874, 1,
 'The largest leprosy-focused non-governmental organisation in India, providing medical care and rehabilitation for people affected by leprosy and other neglected tropical diseases. It runs hospitals, vocational training centres and community projects across nine states. Address: CNI Bhavan, 16, Pandit Pant Marg, New Delhi - 110001',
 'info@leprosymission.in', '+91 11 4353 3300', 'https://www.leprosymission.in');
-- ============================================================
--     * Flask runs on 0.0.0.0, so the site is reachable
--       from other computers.
--     * A dedicated MySQL user was created:
--         CREATE USER 'ngoadmin'@'%' IDENTIFIED BY 'ngo123';
--         GRANT ALL PRIVILEGES ON NGODatabase.* TO 'ngoadmin'@'%';
--
--   STILL NEEDED (run as Administrator, ONCE):
--     1. Allow port 5000 (and 3306 if you want direct DB access)
--        through Windows Firewall:
--          netsh advfirewall firewall add rule name="Flask donateNgo"
--            dir=in action=allow protocol=TCP localport=5000
--          netsh advfirewall firewall add rule name="MySQL LAN"
--            dir=in action=allow protocol=TCP localport=3306
--     2. Find this machine's LAN IP:  ipconfig
--        Other computers then browse to:  http://<this-machine-ip>:5000
--
-- ============================================================
