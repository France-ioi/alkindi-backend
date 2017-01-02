
# CREATE DATABASE alkindi;
# CREATE USER alkindi@localhost IDENTIFIED BY 'woolcorklessjunior';
# GRANT ALL PRIVILEGES ON alkindi.* TO alkindi@localhost;
# FLUSH PRIVILEGES;

# echo "select table_name, constraint_name from information_schema.key_column_usage where constraint_name like 'fk_%';" | mysql alkindi | awk '{ print "ALTER TABLE " $1 " DROP FOREIGN KEY " $2 ";" }'

DROP TABLE IF EXISTS badges CASCADE;
DROP TABLE IF EXISTS questions CASCADE;
DROP TABLE IF EXISTS rounds CASCADE;
DROP TABLE IF EXISTS team_members CASCADE;
DROP TABLE IF EXISTS teams CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS workspace_revisions CASCADE;
DROP TABLE IF EXISTS workspaces CASCADE;

CREATE TABLE users (
    id BIGINT NOT NULL AUTO_INCREMENT,
    created_at DATETIME NOT NULL,
    foreign_id TEXT NOT NULL,
    team_id BIGINT NULL,
    username TEXT NOT NULL,
    PRIMARY KEY (id)
) CHARACTER SET utf8 ENGINE=InnoDB;
CREATE UNIQUE INDEX ix_users__foreign_id USING btree ON users (foreign_id(64));
CREATE INDEX ix_users__team_id USING btree ON users (team_id);

CREATE TABLE teams (
    id BIGINT NOT NULL AUTO_INCREMENT,
    created_at DATETIME NOT NULL,
    round_id BIGINT NOT NULL,
    question_id BIGINT NULL,
    code TEXT NOT NULL,
    is_open BOOLEAN NOT NULL,
    PRIMARY KEY (id)
) CHARACTER SET utf8 ENGINE=InnoDB;
CREATE INDEX ix_teams__round_id USING btree ON teams (round_id);
CREATE INDEX ix_teams__question_id USING btree ON teams (question_id);

CREATE TABLE team_members (
    team_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    joined_at DATETIME NOT NULL,
    is_selected BOOLEAN NOT NULL,
    is_creator BOOLEAN NOT NULL,
    PRIMARY KEY (team_id, user_id)
) CHARACTER SET utf8 ENGINE=InnoDB;
CREATE INDEX ix_team_members__user_id USING btree ON team_members (user_id);

CREATE TABLE rounds (
    id BIGINT NOT NULL AUTO_INCREMENT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    title TEXT NOT NULL,
    allow_register BOOLEAN NOT NULL,
    register_from DATE NOT NULL,
    register_until DATE NOT NULL,
    allow_access BOOLEAN NOT NULL,
    access_from DATE NOT NULL,
    access_until DATE NOT NULL,
    min_team_size INTEGER NOT NULL,
    max_team_size INTEGER NOT NULL,
    min_team_ratio DECIMAL(4,3) NOT NULL,
    questions_path TEXT NOT NULL,
    PRIMARY KEY (id)
) CHARACTER SET utf8 ENGINE=InnoDB;

CREATE TABLE badges (
    id BIGINT NOT NULL AUTO_INCREMENT,
    is_active BOOLEAN NOT NULL,
    symbol TEXT NOT NULL,
    round_id BIGINT NOT NULL,
    PRIMARY KEY (id)
) CHARACTER SET utf8 ENGINE=InnoDB;
CREATE INDEX ix_badges__symbol USING btree ON badges (is_active, symbol(20));
CREATE INDEX ix_badges__round_id USING btree ON badges (round_id);

CREATE TABLE questions (
    id BIGINT NOT NULL AUTO_INCREMENT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    round_id BIGINT NOT NULL,
    data_path TEXT NOT NULL,
    full_data TEXT NOT NULL,
    team_data TEXT NOT NULL,
    PRIMARY KEY (id)
) CHARACTER SET utf8 ENGINE=InnoDB;
CREATE INDEX ix_questions__round_id USING btree ON questions (round_id);

CREATE TABLE workspaces (
    id BIGINT NOT NULL AUTO_INCREMENT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    team_id BIGINT NOT NULL,
    title TEXT NOT NULL,
    PRIMARY KEY (id)
) CHARACTER SET utf8 ENGINE=InnoDB;
CREATE INDEX ix_workspaces__team_id USING btree ON workspaces (team_id);

CREATE TABLE workspace_revisions (
    id BIGINT NOT NULL AUTO_INCREMENT,
    title TEXT NULL,
    workspace_id BIGINT NOT NULL,
    created_at DATETIME NOT NULL,
    parent_id BIGINT NULL,
    is_active BOOLEAN NOT NULL,
    is_precious BOOLEAN NOT NULL,
    state TEXT NOT NULL,
    PRIMARY KEY (id)
) CHARACTER SET utf8 ENGINE=InnoDB;
CREATE INDEX ix_workspace_revisions__workspace_id USING btree ON workspace_revisions (workspace_id);
CREATE INDEX ix_workspace_revisions__parent_id USING btree ON workspace_revisions (parent_id);

ALTER TABLE users ADD CONSTRAINT fk_users__team_id
    FOREIGN KEY ix_users__team_id (team_id) REFERENCES teams(id) ON DELETE SET NULL;
ALTER TABLE teams ADD CONSTRAINT fk_teams__round_id
    FOREIGN KEY (round_id) REFERENCES rounds(id) ON DELETE CASCADE;
ALTER TABLE teams ADD CONSTRAINT fk_teams__question_id
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE SET NULL;
ALTER TABLE team_members ADD CONSTRAINT fk_team_members__team_id
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE;
ALTER TABLE team_members ADD CONSTRAINT fk_team_members__user_id
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE badges ADD CONSTRAINT fk_badges__round_id
    FOREIGN KEY (round_id) REFERENCES rounds(id) ON DELETE CASCADE;
ALTER TABLE questions ADD CONSTRAINT fk_questions__round_id
    FOREIGN KEY (round_id) REFERENCES rounds(id) ON DELETE CASCADE;
ALTER TABLE workspaces ADD CONSTRAINT fk_workspaces__team_id
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE;
ALTER TABLE workspace_revisions ADD CONSTRAINT fk_workspace_revisions__workspace_id
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;
ALTER TABLE workspace_revisions ADD CONSTRAINT fk_workspace_revisions__parent_id
    FOREIGN KEY (parent_id) REFERENCES workspace_revisions(id) ON DELETE SET NULL;

ALTER TABLE users
  ADD COLUMN firstname TEXT NOT NULL DEFAULT '',
  ADD COLUMN lastname TEXT NOT NULL DEFAULT '';

ALTER TABLE team_members ADD COLUMN code TEXT NULL;
ALTER TABLE team_members ADD COLUMN is_unlocked BOOLEAN DEFAULT FALSE;

ALTER TABLE workspaces ADD COLUMN round_id BIGINT NOT NULL;
CREATE INDEX ix_workspaces__round_id USING btree ON workspaces (round_id);
ALTER TABLE workspaces ADD CONSTRAINT fk_workspaces__round_id
    FOREIGN KEY (round_id) REFERENCES rounds(id) ON DELETE CASCADE;

ALTER TABLE questions DROP FOREIGN KEY fk_questions__round_id;
ALTER TABLE questions DROP COLUMN round_id;

CREATE TABLE attempts (
    id BIGINT NOT NULL AUTO_INCREMENT,
    team_id BIGINT NOT NULL,
    round_id BIGINT NOT NULL,
    question_id BIGINT NULL,
    created_at DATETIME NOT NULL,
    closes_at DATETIME NULL,
    is_current BOOLEAN NOT NULL,
    is_training BOOLEAN NOT NULL,
    PRIMARY KEY (id)
) CHARACTER SET utf8 ENGINE=InnoDB;
CREATE INDEX ix_attempts__team_id USING btree ON attempts (team_id);
CREATE INDEX ix_attempts__round_id USING btree ON attempts (round_id);
CREATE INDEX ix_attempts__question_id USING btree ON attempts (question_id);
ALTER TABLE attempts ADD CONSTRAINT fk_attempts__team_id
  FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE;
ALTER TABLE attempts ADD CONSTRAINT fk_attempts__round_id
  FOREIGN KEY (round_id) REFERENCES rounds(id) ON DELETE CASCADE;
ALTER TABLE attempts ADD CONSTRAINT fk_attempts__question_id
  FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE SET NULL;

ALTER TABLE team_members DROP COLUMN code;
ALTER TABLE team_members DROP COLUMN is_unlocked;

ALTER TABLE users ADD COLUMN badges TEXT NOT NULL DEFAULT '';

ALTER TABLE teams ADD COLUMN revision INT NOT NULL DEFAULT 0;
ALTER TABLE teams ADD COLUMN message TEXT NULL;

ALTER TABLE teams DROP FOREIGN KEY fk_teams__question_id;
ALTER TABLE teams DROP COLUMN question_id;

ALTER TABLE attempts ADD COLUMN started_at DATETIME NULL;

ALTER TABLE teams ADD COLUMN is_locked BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE rounds DROP COLUMN allow_access;
ALTER TABLE rounds DROP COLUMN access_from;
ALTER TABLE rounds DROP COLUMN access_until;
ALTER TABLE rounds ADD COLUMN training_opens_at DATETIME NOT NULL;
UPDATE rounds SET training_opens_at = '2016-01-09 07:00:00';

ALTER TABLE rounds DROP COLUMN allow_register;
ALTER TABLE rounds DROP COLUMN register_from;
ALTER TABLE rounds DROP COLUMN register_until;
ALTER TABLE rounds ADD COLUMN registration_opens_at DATETIME NOT NULL;
UPDATE rounds SET registration_opens_at = '2016-01-04 08:00:00';

ALTER TABLE team_members CHANGE COLUMN is_selected is_qualified BOOLEAN NOT NULL;

ALTER TABLE attempts ADD COLUMN is_unsolved BOOLEAN NOT NULL;

ALTER TABLE rounds ADD COLUMN max_attempts INTEGER NOT NULL;
UPDATE rounds SET max_attempts = 3;

CREATE TABLE access_codes (
    attempt_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    code TEXT NOT NULL,
    is_unlocked BOOLEAN NOT NULL,
    PRIMARY KEY (attempt_id, user_id)
) CHARACTER SET utf8 ENGINE=InnoDB;
CREATE INDEX ix_access_codes__user_id USING btree ON access_codes (user_id);
ALTER TABLE access_codes ADD CONSTRAINT fk_access_codes__attempt_id
  FOREIGN KEY (attempt_id) REFERENCES attempts(id) ON DELETE CASCADE;
ALTER TABLE access_codes ADD CONSTRAINT fk_access_codes__user_id
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE attempts DROP FOREIGN KEY fk_attempts__question_id;
ALTER TABLE attempts DROP INDEX ix_attempts__question_id;
ALTER TABLE attempts DROP COLUMN question_id;
ALTER TABLE rounds CHANGE COLUMN questions_path tasks_path TEXT NOT NULL;
DROP TABLE questions;

CREATE TABLE tasks (
    attempt_id BIGINT NOT NULL,
    created_at DATETIME NOT NULL,
    full_data TEXT NOT NULL,
    team_data TEXT NOT NULL,
    PRIMARY KEY (attempt_id)
) CHARACTER SET utf8 ENGINE=InnoDB;
ALTER TABLE tasks ADD CONSTRAINT fk_tasks__attempt_id
  FOREIGN KEY (attempt_id) REFERENCES attempts(id) ON DELETE CASCADE;

UPDATE rounds SET tasks_path = '/home/sebc/alkindi/tasks/playfair/INDEX';

ALTER TABLE rounds ADD COLUMN duration INT NOT NULL;
UPDATE rounds SET duration = 60;

ALTER TABLE rounds ADD COLUMN pre_task_html TEXT NOT NULL;
ALTER TABLE rounds ADD COLUMN post_task_html TEXT NOT NULL;

ALTER TABLE workspace_revisions ADD COLUMN creator_id bigint(20) NOT NULL;
ALTER TABLE workspace_revisions ADD INDEX ix_workspace_revisions__creator_id (creator_id) USING BTREE;
ALTER TABLE workspace_revisions ADD CONSTRAINT fk_workspace_revisions__creator_id FOREIGN KEY (creator_id) REFERENCES users (id) ON DELETE CASCADE;

ALTER TABLE tasks ADD COLUMN task_dir TEXT NOT NULL;

ALTER TABLE rounds DROP COLUMN pre_task_html;
ALTER TABLE rounds DROP COLUMN post_task_html;
ALTER TABLE rounds ADD COLUMN task_url TEXT NOT NULL;

CREATE TABLE errors (
    id BIGINT NOT NULL AUTO_INCREMENT,
    user_id BIGINT NULL,
    created_at DATETIME NOT NULL,
    request_url TEXT NOT NULL,
    request_body BLOB NOT NULL,
    request_headers TEXT NOT NULL,
    context TEXT NOT NULL,
    response_body TEXT NOT NULL,
    PRIMARY KEY (id)
) CHARACTER SET utf8 ENGINE=InnoDB;
-- no foreign keys on table errors, for performance reasons

ALTER TABLE workspaces ADD COLUMN attempt_id BIGINT NULL;
ALTER TABLE workspaces ADD INDEX ix_workspaces__attempt_id (attempt_id) USING BTREE;
ALTER TABLE workspaces ADD CONSTRAINT fk_workspaces__attempt_id FOREIGN KEY (attempt_id) REFERENCES attempts (id) ON DELETE CASCADE;
UPDATE workspaces, attempts SET workspaces.attempt_id = attempts.id WHERE attempts.team_id = workspaces.team_id;

-- /!\ update backend

UPDATE workspaces, attempts SET workspaces.attempt_id = attempts.id WHERE attempts.team_id = workspaces.team_id;

ALTER TABLE workspaces DROP FOREIGN KEY fk_workspaces__team_id;
ALTER TABLE workspaces DROP FOREIGN KEY fk_workspaces__round_id;
ALTER TABLE workspaces DROP COLUMN team_id;
ALTER TABLE workspaces DROP COLUMN round_id;

ALTER TABLE rounds ADD COLUMN max_answers INTEGER NULL;

CREATE TABLE answers (
    id BIGINT NOT NULL AUTO_INCREMENT,
    attempt_id BIGINT NOT NULL,
    submitter_id BIGINT NOT NULL,
    ordinal INT NOT NULL,
    created_at DATETIME NOT NULL,
    answer TEXT NOT NULL,
    grading TEXT NOT NULL,
    score DECIMAL(6,0) NOT NULL,
    is_solution BOOLEAN NOT NULL,
    PRIMARY KEY (id)
) CHARACTER SET utf8 ENGINE=InnoDB;
ALTER TABLE answers ADD INDEX ix_answers__attempt_id_ordinal (attempt_id, ordinal) USING BTREE;
ALTER TABLE answers ADD CONSTRAINT fk_answers__attempt_id FOREIGN KEY (attempt_id) REFERENCES attempts (id) ON DELETE CASCADE;
CREATE INDEX ix_answers__submitter_id USING btree ON answers (submitter_id);
ALTER TABLE answers ADD CONSTRAINT fk_answers__submitter_id
  FOREIGN KEY (submitter_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE attempts ADD COLUMN is_fully_solved BOOLEAN NOT NULL DEFAULT FALSE;


ALTER TABLE attempts ADD COLUMN ordinal INT NOT NULL;;

SET @ordinal := 0;
SET @team_id := 0;
UPDATE attempts AS t, (SELECT id, @ordinal := CASE WHEN @team_id = team_id THEN @ordinal + 1 ELSE 0 END AS ordinal, @team_id := team_id AS team_id FROM attempts WHERE round_id = 2 ORDER BY team_id, id) AS s SET t.ordinal = s.ordinal WHERE t.id = s.id;

DELETE FROM attempts WHERE round_id = 1;

ALTER TABLE attempts ADD UNIQUE INDEX ix_attempts__team_id_round_id_ordinal (team_id, round_id, ordinal) USING BTREE;

ALTER TABLE answers ADD COLUMN is_full_solution BOOLEAN NOT NULL;
ALTER TABLE answers ADD COLUMN feedback TEXT NOT NULL DEFAULT '';

ALTER TABLE teams MODIFY COLUMN code TEXT NULL;
ALTER TABLE teams ADD COLUMN score DECIMAL(6,0) NULL;
ALTER TABLE rounds ADD COLUMN status TEXT NOT NULL;
UPDATE rounds SET status = 'open';

ALTER TABLE teams ADD COLUMN parent_id BIGINT NULL;
CREATE INDEX ix_teams__parent_id USING btree ON teams (parent_id);
ALTER TABLE teams ADD CONSTRAINT fk_teams__parent_id
    FOREIGN KEY ix_teams__parent_id (parent_id) REFERENCES teams(id) ON DELETE SET NULL;

ALTER TABLE rounds MODIFY COLUMN max_attempts INTEGER NULL;

INSERT INTO rounds (
  created_at, updated_at,
  title,
  min_team_size, max_team_size, min_team_ratio,
  tasks_path, training_opens_at, registration_opens_at,
  max_attempts, duration, max_answers,
  status
) VALUES (
  NOW(), NOW(),
  'Concours Alkindi 2015-2016 tour 3',
  1, 4, 0.5,
  '/home/alkindi/tasks/adfgx/INDEX',
  '2016-01-25 07:00:00', '2016-01-23 19:00:00',
  NULL, 60, NULL,
  'prepared'
);

ALTER TABLE rounds ADD COLUMN allow_team_changes BOOLEAN NOT NULL;
ALTER TABLE rounds ADD COLUMN have_training_attempt BOOLEAN NOT NULL;
ALTER TABLE rounds ADD COLUMN task_module TEXT NOT NULL;
UPDATE rounds SET allow_team_changes = 1 WHERE id = 2;
UPDATE rounds SET have_training_attempt = 1 WHERE id = 2;
UPDATE rounds SET task_module = 'alkindi.tasks.playfair' WHERE id = 2;

UPDATE rounds SET training_opens_at = now() WHERE id = 3;
UPDATE rounds SET training_opens_at = '2016-01-25 07:00:00' where id = 3;
UPDATE rounds SET task_module = 'alkindi.tasks.adfgx' WHERE id = 3;

UPDATE rounds SET status = 'open' WHERE id = 3;

ALTER TABLE rounds ADD COLUMN task_front TEXT NOT NULL;
UPDATE rounds SET task_front = 'playfair' WHERE id = 1;
UPDATE rounds SET task_front = 'adfgx' WHERE id = 3;

---

# Delete round 1 (test round) attempts.
DELETE FROM attempts WHERE round_id = 1;

CREATE TABLE participations (
    id BIGINT NOT NULL AUTO_INCREMENT,
    team_id BIGINT NOT NULL,
    round_id BIGINT NOT NULL,
    created_at DATETIME NOT NULL,
    score DECIMAL(6,0) NULL,
    PRIMARY KEY (id)
) CHARACTER SET utf8 ENGINE=InnoDB;
CREATE INDEX ix_participations__round_id USING btree ON participations (round_id);

# Attempts and workspaces will be associated with a participation.
ALTER TABLE attempts ADD COLUMN participation_id BIGINT NOT NULL;

# Add some temporary indexes.
CREATE INDEX ix_participations__team_id USING btree ON participations (team_id);
CREATE INDEX ix_attempts__participation_id USING btree ON attempts (participation_id);

# Create a participation for each (team_id, round_id) pair.
INSERT INTO participations (team_id, round_id, created_at)
    SELECT teams.id, teams.round_id, created_at FROM teams;
# Set a participation id on each attempt, workspace.
UPDATE attempts a
    JOIN participations p ON p.team_id = a.team_id
    SET participation_id = p.id;
# In participations, overwrite each team's id with its parent team's id.
# /!\ Run the query until there are 0 rows matched.
UPDATE participations p
    JOIN teams t ON p.team_id = t.id
    SET team_id = t.parent_id
    WHERE t.parent_id IS NOT NULL;
# Do the same for users.
UPDATE users u
    JOIN teams t ON u.team_id = t.id
    SET team_id = t.parent_id
    WHERE t.parent_id IS NOT NULL;
# Some teams now have more than one participation for round 3.
# Associate their attempts to the participation with the smallest id.
# [47 rows matched]
UPDATE attempts a JOIN (
    SELECT p1.id old_id, MIN(p2.id) new_id
        FROM participations p1
        INNER JOIN participations p2
            ON p1.team_id = p2.team_id
            AND p1.round_id = p2.round_id
        GROUP BY p1.id) t
    SET a.participation_id = t.new_id
    WHERE a.participation_id = t.old_id
    AND t.new_id <> t.old_id;
# Delete the (now orphaned) duplicate participations.
# [37 rows matched]
DELETE p.*
    FROM participations p,
    (SELECT p1.id old_id, MIN(p2.id) new_id
        FROM participations p1
        INNER JOIN participations p2
            ON p1.team_id = p2.team_id
            AND p1.round_id = p2.round_id
        GROUP BY p1.id) t
    WHERE t.old_id <> t.new_id
    AND p.id = t.old_id;
# Compute participation scores.
UPDATE participations p
    JOIN (
        SELECT at.participation_id id, MAX(an.score) max_score
        FROM attempts at
        INNER JOIN answers an ON an.attempt_id = at.id
        GROUP BY at.participation_id
    ) t
    ON t.id = p.id
    SET p.score = t.max_score;

# Renumber the attempts sequentially within each participation.
ALTER TABLE attempts DROP INDEX ix_attempts__team_id_round_id_ordinal;
SET @ordinal := 0;
SET @participation_id := 0;
UPDATE attempts AS t,
    (
        SELECT id, @ordinal :=
            CASE
                WHEN @participation_id = participation_id THEN @ordinal + 1
                ELSE 0
            END AS ordinal,
            @participation_id := participation_id AS participation_id
        FROM attempts WHERE round_id = 3 ORDER BY participation_id, id) AS s
    SET t.ordinal = s.ordinal WHERE t.id = s.id;

# Replace the temporary indexes with the final ones.
ALTER TABLE participations DROP INDEX ix_participations__team_id;
ALTER TABLE attempts DROP INDEX ix_attempts__participation_id;
CREATE UNIQUE INDEX ix_participations__team_id_round_id USING btree ON participations (team_id, round_id);
CREATE UNIQUE INDEX ix_attempts__participation_id_ordinal USING BTREE ON attempts (participation_id, ordinal);

# Add foreign keys.
ALTER TABLE participations ADD CONSTRAINT fk_participations__team_id
  FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE;
ALTER TABLE participations ADD CONSTRAINT fk_participations__round_id
  FOREIGN KEY (round_id) REFERENCES rounds(id) ON DELETE CASCADE;
ALTER TABLE attempts ADD CONSTRAINT fk_attempts__participation_id
  FOREIGN KEY (participation_id) REFERENCES participations(id) ON DELETE CASCADE;

# Discard the now unused foreign keys.
ALTER TABLE teams DROP FOREIGN KEY fk_teams__round_id;
ALTER TABLE teams DROP FOREIGN KEY fk_teams__parent_id;
ALTER TABLE attempts DROP FOREIGN KEY fk_attempts__team_id;
ALTER TABLE attempts DROP FOREIGN KEY fk_attempts__round_id;

# Delete child teams, they are no longer useful (cascades to team_members).
DELETE FROM teams WHERE parent_id IS NOT NULL;

# Discard unused columns.
ALTER TABLE attempts DROP COLUMN team_id;
ALTER TABLE attempts DROP COLUMN round_id;
ALTER TABLE teams DROP COLUMN round_id;
ALTER TABLE teams DROP COLUMN parent_id;
ALTER TABLE teams DROP COLUMN score;
ALTER TABLE teams DROP COLUMN revision;
ALTER TABLE teams DROP COLUMN message;

# Rounds can have a null duration.
ALTER TABLE rounds MODIFY COLUMN duration INT NULL;
ALTER TABLE rounds ADD COLUMN hide_scores BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE participations ADD COLUMN is_qualified BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE `teams` ADD `rank` INT(11) NULL DEFAULT NULL;
ALTER TABLE `teams` ADD `rank_region` INT(11) NULL DEFAULT NULL;;

CREATE TABLE `regions` (
    id BIGINT NOT NULL AUTO_INCREMENT,
    name TEXT NOT NULL,
    code TEXT NOT NULL,
    PRIMARY KEY (id)
) CHARACTER SET utf8 ENGINE=InnoDB;

ALTER TABLE teams ADD COLUMN region_id BIGINT NULL DEFAULT NULL;
ALTER TABLE teams ADD INDEX ix_teams__region_id (region_id) USING BTREE;
ALTER TABLE teams ADD CONSTRAINT fk_teams__region_id
    FOREIGN KEY ix_teams__region_id (region_id) REFERENCES regions(id)
    ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE `participations` ADD COLUMN `score_90min` decimal(6,0) DEFAULT NULL;
ALTER TABLE `participations` ADD COLUMN `first_equal_90min` smallint DEFAULT NULL;
ALTER TABLE `participations` ADD COLUMN `is_qualified` boolean DEFAULT NULL;

ALTER TABLE `users` ADD COLUMN `is_admin` tinyint(1) NOT NULL DEFAULT '0';

---

RENAME TABLE `tasks` TO `task_instances`;
-- Column task_dir is removed, will be included in full_data.
ALTER TABLE `task_instances` DROP COLUMN `task_dir`;
-- Update FK name.
ALTER TABLE `task_instances` DROP FOREIGN KEY `fk_tasks__attempt_id`;
ALTER TABLE `task_instances` ADD CONSTRAINT `fk_task_instances__attempt_id`
  FOREIGN KEY (`attempt_id`) REFERENCES `attempts` (`id`)
  ON DELETE CASCADE ON UPDATE CASCADE;

-- Platform/task communication will all go through backend_url.
CREATE TABLE `tasks` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `title` text NOT NULL,
  `backend_url` text NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Table round_tasks holds the task settings (default values may be
-- provided by the task's backend)
CREATE TABLE `round_tasks` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `round_id` bigint(20) NOT NULL,
  `task_id` bigint(20) NOT NULL,
  `rank` int(11) NOT NULL DEFAULT '0',
  `duration` int(11) DEFAULT NULL,
  `max_attempts` int(11) DEFAULT NULL,
  `max_answers` int(11) DEFAULT NULL,
  `hide_scores` tinyint(1) NOT NULL DEFAULT '0',
  `have_training_attempt` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (id)
) ENGINE=InnoDB;
ALTER TABLE `round_tasks` ADD INDEX `ix_round_tasks__round_rank` (round_id, rank) USING BTREE;
ALTER TABLE `round_tasks` ADD INDEX `ix_round_tasks__task_id` (task_id) USING BTREE;
ALTER TABLE `round_tasks` ADD CONSTRAINT `fk_round_tasks__round_id`
  FOREIGN KEY `ix_round_tasks__round_rank` (`round_id`) REFERENCES `rounds` (`id`)
  ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE `round_tasks` ADD CONSTRAINT `fk_round_tasks__task_id`
  FOREIGN KEY `ix_round_tasks__task_id` (`task_id`) REFERENCES `tasks` (`id`)
  ON DELETE CASCADE ON UPDATE CASCADE;

-- Every attempt now relates to a task.
ALTER TABLE `attempts` ADD COLUMN `task_id` bigint(20) NOT NULL;
ALTER TABLE `attempts` ADD CONSTRAINT `fk_attempts__task_id`
  FOREIGN KEY (`task_id`) REFERENCES `tasks` (`id`) ON DELETE CASCADE;

-- The best score will be cached in every attempt.
ALTER TABLE `attempts` ADD COLUMN `score` decimal(6,0) DEFAULT NULL;

-- Participations would benefit from an updated_at column.
ALTER TABLE `participations` ADD COLUMN `updated_at` datetime NOT NULL;

-- Clean up now-unused columns.
ALTER TABLE `rounds` DROP COLUMN `task_front`;
ALTER TABLE `rounds` DROP COLUMN `task_module`;
ALTER TABLE `rounds` DROP COLUMN `task_url`;
ALTER TABLE `rounds` DROP COLUMN `tasks_path`;
ALTER TABLE `rounds` DROP COLUMN `max_attempts`;
ALTER TABLE `rounds` DROP COLUMN `max_answers`;
ALTER TABLE `rounds` DROP COLUMN `hide_scores`;
ALTER TABLE `rounds` DROP COLUMN `have_training_attempt`;

ALTER TABLE `round_tasks` ADD COLUMN `use_codes` tinyint(1) NOT NULL DEFAULT '0';
ALTER TABLE `round_tasks` CHANGE COLUMN `rank` `ordinal` int(11) NOT NULL DEFAULT '0';
ALTER TABLE `round_tasks` CHANGE COLUMN `duration` `attempt_duration` int(11) DEFAULT NULL;
ALTER TABLE `round_tasks` CHANGE COLUMN `max_answers` `max_attempt_answers` int(11) DEFAULT NULL;
ALTER TABLE `round_tasks` CHANGE COLUMN `max_attempts` `max_timed_attempts` int(11) DEFAULT NULL;

