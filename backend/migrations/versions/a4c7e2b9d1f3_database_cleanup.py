"""database cleanup: drop tournaments, AI matches, unused user columns; add
achievement words, Elo history, stats rows and indexes

Revision ID: a4c7e2b9d1f3
Revises: 8bb45a0b1a9e
Create Date: 2026-11-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a4c7e2b9d1f3'
down_revision: Union[str, Sequence[str], None] = '8bb45a0b1a9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_foreign_key(table: str, column: str) -> None:
    """Drop the foreign key on `column`. The first migration let MySQL name
    them (matches_ibfk_3...), so look the name up instead of guessing."""
    for fk in sa.inspect(op.get_bind()).get_foreign_keys(table):
        if fk['constrained_columns'] == [column]:
            op.drop_constraint(fk['name'], table, type_='foreignkey')
            return
    raise RuntimeError(f'No foreign key on {table}.{column}.')


def upgrade() -> None:
    """Upgrade schema."""
    # Tournaments and AI matches are out of scope.
    _drop_foreign_key('matches', 'tournament_id')
    op.drop_column('matches', 'tournament_id')
    op.drop_column('matches', 'tournament_round')
    op.drop_column('matches', 'is_ai_match')
    op.drop_column('matches', 'ai_difficulty')
    op.drop_table('tournament_participants')
    op.drop_table('tournaments')

    # 2FA codes are emailed and kept in Redis; user_stats.rating_elo is the
    # one Elo rating.
    op.drop_column('users', 'two_factor_secret')
    op.drop_column('users', 'elo')

    # Every user gets a stats row, so /users/{id}/stats and matchmaking work.
    op.alter_column('user_stats', 'rating_elo', existing_type=sa.Integer(),
                    server_default='1200', existing_nullable=False)
    op.execute(
        'INSERT INTO user_stats (user_id, matches_played, wins, losses, draws, '
        'rating_elo, highest_word_score, total_damage_dealt) '
        'SELECT users.id, 0, 0, 0, 0, 1200, 0, 0 FROM users '
        'LEFT JOIN user_stats ON user_stats.user_id = users.id '
        'WHERE user_stats.user_id IS NULL'
    )
    op.create_index('ix_user_stats_rating_elo', 'user_stats', ['rating_elo'])
    op.create_index('ix_user_stats_wins', 'user_stats', ['wins'])

    op.add_column('matches', sa.Column('player1_elo_before', sa.Integer(), nullable=True))
    op.add_column('matches', sa.Column('player1_elo_after', sa.Integer(), nullable=True))
    op.add_column('matches', sa.Column('player2_elo_before', sa.Integer(), nullable=True))
    op.add_column('matches', sa.Column('player2_elo_after', sa.Integer(), nullable=True))

    op.create_unique_constraint(
        'uq_match_casts_match_turn', 'match_casts', ['match_id', 'turn_number']
    )
    # A downgrade leaves this index behind; the unique index covers it.
    indexes = sa.inspect(op.get_bind()).get_indexes('match_casts')
    if any(index['name'] == 'ix_match_casts_match_id' for index in indexes):
        op.drop_index('ix_match_casts_match_id', table_name='match_casts')

    op.create_table('achievement_words',
    sa.Column('achievement_id', sa.String(length=32), nullable=False),
    sa.Column('word', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['achievement_id'], ['achievements.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('achievement_id', 'word')
    )
    op.create_table('user_achievement_words',
    sa.Column('user_id', sa.BINARY(length=16), nullable=False),
    sa.Column('achievement_id', sa.String(length=32), nullable=False),
    sa.Column('word', sa.String(length=32), nullable=False),
    sa.Column('found_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['achievement_id', 'word'], ['achievement_words.achievement_id', 'achievement_words.word'], name='fk_user_achievement_words_word', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'achievement_id', 'word')
    )


def downgrade() -> None:
    """Downgrade schema. Dropped data (tournaments, 2FA secrets, users.elo)
    doesn't come back; the columns return with their old defaults."""
    op.drop_table('user_achievement_words')
    op.drop_table('achievement_words')
    # MySQL now uses the unique index for the match_id foreign key; give the
    # key its own index before dropping it.
    op.create_index('ix_match_casts_match_id', 'match_casts', ['match_id'])
    op.drop_constraint('uq_match_casts_match_turn', 'match_casts', type_='unique')
    op.drop_column('matches', 'player2_elo_after')
    op.drop_column('matches', 'player2_elo_before')
    op.drop_column('matches', 'player1_elo_after')
    op.drop_column('matches', 'player1_elo_before')
    op.drop_index('ix_user_stats_wins', table_name='user_stats')
    op.drop_index('ix_user_stats_rating_elo', table_name='user_stats')
    op.alter_column('user_stats', 'rating_elo', existing_type=sa.Integer(),
                    server_default=None, existing_nullable=False)

    op.add_column('users', sa.Column('elo', sa.Integer(), server_default='1', nullable=False))
    op.add_column('users', sa.Column('two_factor_secret', sa.String(length=64), nullable=True))

    op.create_table('tournaments',
    sa.Column('id', sa.BINARY(length=16), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('max_participants', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('REGISTRATION', 'IN_PROGRESS', 'COMPLETED', 'CANCELED', name='tournamentstatus'), nullable=False),
    sa.Column('winner_id', sa.BINARY(length=16), nullable=True),
    sa.Column('created_by', sa.BINARY(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['winner_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('tournament_participants',
    sa.Column('tournament_id', sa.BINARY(length=16), nullable=False),
    sa.Column('user_id', sa.BINARY(length=16), nullable=False),
    sa.Column('seed', sa.Integer(), nullable=False),
    sa.Column('joined_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['tournament_id'], ['tournaments.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('tournament_id', 'user_id')
    )
    op.add_column('matches', sa.Column('ai_difficulty', sa.Enum('EASY', 'MEDIUM', 'HARD', name='aidifficulty'), nullable=True))
    op.add_column('matches', sa.Column('is_ai_match', sa.Boolean(), server_default='0', nullable=False))
    op.add_column('matches', sa.Column('tournament_round', sa.Integer(), nullable=True))
    op.add_column('matches', sa.Column('tournament_id', sa.BINARY(length=16), nullable=True))
    op.create_foreign_key(None, 'matches', 'tournaments', ['tournament_id'], ['id'], ondelete='SET NULL')
