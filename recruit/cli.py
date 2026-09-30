"""命令行入口：跑公会招募样例。"""

import argparse

from .core import EXPIRE_MS, Recruit


def build_parser():
    parser = argparse.ArgumentParser(prog="guild-recruit", description="公会招募")
    parser.add_argument("--sample", default="level", help="level / quota / dup / expire")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.sample == "level":
        book = Recruit(min_level=10)
        print("ok=%s" % str(book.apply("a-1", "p", 5, 0)).lower())
    elif args.sample == "quota":
        book = Recruit(quota=1)
        book.apply("a-1", "p", 50, 0)
        book.accept("a-1")
        book.apply("a-2", "q", 50, 10)
        print("second=%s" % str(book.accept("a-2")).lower())
    elif args.sample == "dup":
        book = Recruit()
        first = book.apply("a-1", "p", 50, 0)
        second = book.apply("a-1", "p", 50, 10)
        print("second=%s pending=%d" % (str(second).lower(), book.pending(10)))
    elif args.sample == "expire":
        book = Recruit()
        book.apply("a-1", "p", 50, 0)
        print("pending=%d" % book.pending(EXPIRE_MS + 1))
    else:
        raise SystemExit("需要 --sample level|quota|dup|expire")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
