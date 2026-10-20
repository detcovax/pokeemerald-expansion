	.equiv TRACK_SIZE, 0x50
	.equiv NUM_TRACKS_BGM, 16 @ TREY (6a): HGSS songs use up to 16 tracks
	.equiv NUM_TRACKS_SE1, 3
	.equiv NUM_TRACKS_SE2, 11
	.equiv NUM_TRACKS_SE3, 1

	.section .sbss, "aw", %nobits @ TREY (6a): tracks live in EWRAM to keep IWRAM free for the HQ mixer
	.align 2

gMPlayTrack_BGM::
	.space TRACK_SIZE * NUM_TRACKS_BGM
	.size gMPlayTrack_BGM, .-gMPlayTrack_BGM

gMPlayTrack_SE1::
	.space TRACK_SIZE * NUM_TRACKS_SE1
	.size gMPlayTrack_SE1, .-gMPlayTrack_SE1

gMPlayTrack_SE2::
	.space TRACK_SIZE * NUM_TRACKS_SE2
	.size gMPlayTrack_SE2, .-gMPlayTrack_SE2

gMPlayTrack_SE3::
	.space TRACK_SIZE * NUM_TRACKS_SE3
	.size gMPlayTrack_SE3, .-gMPlayTrack_SE3

	.section .rodata

	.align 2
gMPlayTable::
	music_player gMPlayInfo_BGM, gMPlayTrack_BGM, NUM_TRACKS_BGM, 0
	music_player gMPlayInfo_SE1, gMPlayTrack_SE1, NUM_TRACKS_SE1, 1
	music_player gMPlayInfo_SE2, gMPlayTrack_SE2, NUM_TRACKS_SE2, 1
	music_player gMPlayInfo_SE3, gMPlayTrack_SE3, NUM_TRACKS_SE3, 0
