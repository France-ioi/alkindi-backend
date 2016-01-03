
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

#---

CREATE TABLE access_codes (
    attempt_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    code TEXT NOT NULL,
    is_unlocked BOOLEAN NOT NULL,
    PRIMARY KEY (attempt_id, user_id)
) CHARACTER SET utf8 ENGINE=InnoDB;
CREATE INDEX ix_access_codes__attempt_id USING btree ON access_codes (attempt_id);
CREATE INDEX ix_access_codes__user_id USING btree ON access_codes (user_id);
ALTER TABLE access_codes ADD CONSTRAINT fk_access_codes__attempt_id
  FOREIGN KEY (attempt_id) REFERENCES attempts(id) ON DELETE CASCADE;
ALTER TABLE access_codes ADD CONSTRAINT fk_access_codes__user_id
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
